"""Independently extract, test and start the v6 package using available dependencies."""
import ast
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import uuid
import zipfile
from pathlib import PurePosixPath

import httpx
from create_product_v6 import DEST, REQUIRED, ROOT

target = ROOT / "tmp/product-v6-check" / uuid.uuid4().hex
target.mkdir(parents=True, exist_ok=False)
with zipfile.ZipFile(DEST) as archive:
    names = archive.namelist()
    if archive.testzip() or len(names) != len(set(names)): raise SystemExit("Invalid archive")
    for name in names:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or any(part in {"node_modules", ".venv", ".git", "__pycache__"} for part in path.parts): raise SystemExit(f"Unsafe archive entry: {name}")
        if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"): raise SystemExit(f"Private config: {name}")
    archive.extractall(target)
    for name in REQUIRED:
        if not (target / name).is_file(): raise SystemExit(f"Missing file: {name}")
    for name in names:
        file = target / name
        if file.is_file() and hashlib.sha256(file.read_bytes()).digest() != hashlib.sha256(archive.read(name)).digest(): raise SystemExit(f"Checksum mismatch: {name}")
for path in ("frontend/package.json", "frontend/package-lock.json"):
    json.loads((target / path).read_text(encoding="utf-8"))
for path in ("backend/app/api/baseline.py", "data_pipeline/pipeline.py", "scripts/train_text_baseline.py"):
    ast.parse((target / path).read_text(encoding="utf-8"))
for name in ("governance-example", "education-classification-synthetic"):
    path = target / f"demo-datasets/{name}.jsonl"
    if hashlib.sha256(path.read_bytes()).hexdigest() != path.with_suffix(".sha256").read_text(encoding="ascii").strip(): raise SystemExit("Fixture checksum mismatch")
evidence = json.loads((target / "evidence/baseline_acceptance.json").read_text(encoding="utf-8"))
if hashlib.sha256((target / "evidence/baseline/model.joblib").read_bytes()).hexdigest() != evidence["model_sha256"]: raise SystemExit("Evidence model mismatch")
test_env = {**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD":"1", "PYTHONPATH":str(target)}
test = subprocess.run([sys.executable, "-m", "pytest", "data_pipeline/tests", "scripts/module4/tests/test_text_baseline.py", "-q", "--basetemp", str(target / "tmp/pytest")], cwd=target, env=test_env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
if test.returncode: raise SystemExit("Extracted tests failed: " + test.stdout[-3000:] + test.stderr[-1000:])
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]
env = {**test_env, "APP_ENV":"development", "AUTH_MODE":"passwordless", "DEV_AUTH_USERNAME":"admin", "PLATFORM_DEMO_MODE":"1",
       "DATABASE_URL":"sqlite:///" + (target / "tmp/service.db").as_posix(), "PREPROJECT_DATA_DIR":str(target / "tmp/storage"), "BASELINE_PYTHON":sys.executable}
with (target / "tmp/server.log").open("w", encoding="utf-8") as log:
    server = subprocess.Popen([sys.executable,"-m","uvicorn","app.main:app","--host","127.0.0.1","--port",str(port)],cwd=target / "backend", env=env, stdout=log, stderr=log)
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=60, trust_env=False) as client:
            for _ in range(120):
                try:
                    if client.get("/health").status_code == 200: break
                except httpx.TransportError: pass
                if server.poll() is not None: raise RuntimeError("Extracted service exited")
                time.sleep(.25)
            else: raise RuntimeError("Extracted service did not start")
            bootstrap = client.post("/api/preproject-data/examples/bootstrap")
            if bootstrap.status_code != 200 or not bootstrap.json().get("classification_version", {}).get("version_id"): raise RuntimeError("Extracted bootstrap failed")
            version_id = bootstrap.json()["classification_version"]["version_id"]
            versions = client.get("/api/baseline/versions")
            if versions.status_code != 200 or not any(item.get("version_id") == version_id and item.get("compatible") and item.get("is_default") for item in versions.json().get("items", [])):
                raise RuntimeError("Extracted default classification version is unavailable")
            if client.get("/api/baseline/experiments").json().get("items"): raise RuntimeError("Bootstrap unexpectedly trained a model")
            environment = client.get("/api/baseline/environment")
            if environment.status_code != 200 or not environment.json().get("ready"): raise RuntimeError("Extracted baseline check failed")
    finally:
        server.terminate()
        try: server.wait(timeout=10)
        except subprocess.TimeoutExpired: server.kill(); server.wait()
print(json.dumps({"extracted_to":str(target), "entries":len(names), "checksums_match":True, "tests":test.stdout.strip(), "service_started":True, "baseline_fit_check":True}, ensure_ascii=True, indent=2))
