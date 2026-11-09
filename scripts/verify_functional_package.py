"""Extract and check the functional review package in a new isolated directory."""
from __future__ import annotations

import ast
import hashlib
import json
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from create_functional_package import DEST, REQUIRED

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "tmp" / "functional-package-check" / uuid.uuid4().hex
PAGES = ["SourcesPage", "PipelinePage", "TasksPage", "QualityPage", "ReviewsPage", "VersionsPage"]


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(DEST) as archive:
        entries = archive.namelist()
        if archive.testzip() or len(entries) != len(set(entries)):
            raise SystemExit("Archive corruption or duplicate entries")
        for name in entries:
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or any(part in {".git", "node_modules", ".venv", "__pycache__"} for part in path.parts):
                raise SystemExit(f"Unsafe archive entry: {name}")
            if path.name == ".env" or path.name.startswith(".env.") and path.name != ".env.example":
                raise SystemExit(f"Private configuration in archive: {name}")
        archive.extractall(TARGET)
        for name in REQUIRED + [f"frontend/src/pages/PreprojectData/pages/{page}.tsx" for page in PAGES]:
            if not (TARGET / name).is_file():
                raise SystemExit(f"Missing {name}")
        for name in entries:
            path = TARGET / name
            if path.is_file() and hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(archive.read(name)).digest():
                raise SystemExit(f"Extraction mismatch: {name}")
    json.loads((TARGET / "frontend/package.json").read_text(encoding="utf-8"))
    json.loads((TARGET / "frontend/package-lock.json").read_text(encoding="utf-8"))
    for name in ("backend/app/api/module4.py", "backend/app/api/preproject_data.py", "scripts/module4/04_make_eval_manifest.py"):
        ast.parse((TARGET / name).read_text(encoding="utf-8"))
    print(json.dumps({"extracted_to": str(TARGET), "entries": len(entries), "required_files_present": True, "checksums_match": True, "python_syntax": True}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
