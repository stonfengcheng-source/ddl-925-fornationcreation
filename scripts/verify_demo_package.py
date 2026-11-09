"""Extract the demo package to an isolated directory and verify basic CPU tests."""
import ast
import hashlib
import json
import subprocess
import sys
import uuid
import zipfile
from pathlib import PurePosixPath
from create_demo_package import ROOT, DEST, REQUIRED

target = ROOT / "tmp/demo-package-check" / uuid.uuid4().hex
target.mkdir(parents=True, exist_ok=False)
with zipfile.ZipFile(DEST) as archive:
    names = archive.namelist()
    if archive.testzip() or len(names) != len(set(names)): raise SystemExit("Invalid archive")
    for name in names:
        p = PurePosixPath(name)
        if p.is_absolute() or ".." in p.parts or any(part in {"node_modules", ".venv", ".git", "__pycache__"} for part in p.parts): raise SystemExit(f"Unsafe entry: {name}")
        if p.name == ".env" or (p.name.startswith(".env.") and p.name != ".env.example"): raise SystemExit(f"Private config: {name}")
    archive.extractall(target)
    for name in REQUIRED:
        if not (target / name).is_file(): raise SystemExit(f"Missing required file: {name}")
    for name in names:
        path = target / name
        if path.is_file() and hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(archive.read(name)).digest(): raise SystemExit(f"Checksum mismatch: {name}")
json.loads((target / "frontend/package.json").read_text(encoding="utf-8"))
json.loads((target / "frontend/package-lock.json").read_text(encoding="utf-8"))
for name in ("backend/app/api/preproject_data.py", "scripts/default_demo_acceptance.py", "data_pipeline/pipeline.py"):
    ast.parse((target / name).read_text(encoding="utf-8"))
fixture = target / "demo-datasets/governance-example.jsonl"
if hashlib.sha256(fixture.read_bytes()).hexdigest() != fixture.with_suffix('.sha256').read_text(encoding='ascii').strip(): raise SystemExit("Example fixture checksum mismatch")
test = subprocess.run([sys.executable,"-m","pytest","data_pipeline/tests","-q","--basetemp",str(target / "test-temp")], cwd=target, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
if test.returncode: raise SystemExit("Extracted CPU tests failed: " + test.stdout[-3000:] + test.stderr[-1000:])
print(json.dumps({"extracted_to":str(target), "entries":len(names), "checksums_match":True, "cpu_test_output":test.stdout.strip()}, ensure_ascii=True, indent=2))
