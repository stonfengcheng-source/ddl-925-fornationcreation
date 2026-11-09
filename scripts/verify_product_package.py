"""Extract product package to a fresh directory and run its CPU pipeline tests."""
import ast
import hashlib
import json
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from create_product_package import DEST, REQUIRED, ROOT

target = ROOT / "tmp/product-package-check" / uuid.uuid4().hex
target.mkdir(parents=True, exist_ok=False)
with zipfile.ZipFile(DEST) as archive:
    names = archive.namelist()
    if archive.testzip() or len(names) != len(set(names)): raise SystemExit("Corrupt or duplicate ZIP entry")
    for name in names:
        p = PurePosixPath(name)
        if p.is_absolute() or ".." in p.parts or any(part in {"node_modules", ".venv", ".git", "__pycache__"} for part in p.parts): raise SystemExit(f"Unsafe entry: {name}")
        if p.name == ".env" or (p.name.startswith(".env.") and p.name != ".env.example"): raise SystemExit(f"Private config: {name}")
    archive.extractall(target)
    pages = [f"frontend/src/pages/PreprojectData/pages/{name}Page.tsx" for name in ("Sources", "Pipeline", "Tasks", "Quality", "Reviews", "Versions")]
    for name in REQUIRED + pages:
        if not (target / name).is_file(): raise SystemExit(f"Missing required file: {name}")
    for name in names:
        path = target / name
        if path.is_file() and hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(archive.read(name)).digest(): raise SystemExit(f"Extraction mismatch: {name}")
json.loads((target / "frontend/package.json").read_text(encoding="utf-8"))
json.loads((target / "frontend/package-lock.json").read_text(encoding="utf-8"))
for name in ("backend/app/api/module4.py", "backend/app/api/preproject_data.py", "scripts/module4/04_make_eval_manifest.py"):
    ast.parse((target / name).read_text(encoding="utf-8"))
result = subprocess.run([sys.executable, "-m", "pytest", "data_pipeline/tests", "-q", "--basetemp", str(target / "test-temp")], cwd=target, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
if result.returncode: raise SystemExit("Extracted pipeline tests failed:\n" + result.stdout[-4000:] + result.stderr[-1000:])
print(json.dumps({"extracted_to": str(target), "entries": len(names), "checksums_match": True, "pipeline_test_output": result.stdout.strip()}, ensure_ascii=False, indent=2))
