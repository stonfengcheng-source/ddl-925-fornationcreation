"""Build the round-ten review package from source and recorded, redacted evidence."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from create_review_package import ROOT, EVIDENCE, SECRET_RE, eligible, sanitize_text, scrub, source_files

DEST = ROOT / "deliverables/data-platform-functional-fix-v3.zip"
REQUIRED = [
    "frontend/package.json", "frontend/package-lock.json", "frontend/src/pages/Module4/index.tsx",
    "frontend/src/pages/PreprojectData/pages/SourcesPage.tsx", "backend/requirements.txt",
    "backend/app/api/module4.py", "backend/app/api/preproject_data.py", "data_pipeline/pipeline.py",
    "scripts/module4/00_check_environment.py", "scripts/module4/04_make_eval_manifest.py",
    "scripts/module4/08_run_opencompass.py", "scripts/start_demo.ps1", "scripts/stop_demo.ps1",
    "scripts/module4_functional_check.py", "demo-datasets/preproject-test-only.jsonl",
    "docs/functional_fix_report.md", "docs/review_package_readme.md", "evidence/functional_results.json",
]


def main() -> None:
    evidence = ROOT / "tmp/functional-r10/functional_results.json"
    environment = ROOT / "tmp/module4-round10-env.json"
    if not evidence.is_file() or not environment.is_file():
        raise SystemExit("Missing actual functional or environment evidence")
    DEST.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(DEST, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in source_files():
            if not eligible(path):
                continue
            contents = path.read_bytes()
            if path.suffix.lower() == ".md":
                contents = sanitize_text(contents.decode("utf-8")).encode("utf-8")
            if SECRET_RE.search(contents):
                raise SystemExit(f"Possible credential in {path.relative_to(ROOT)}")
            archive.writestr(path.relative_to(ROOT).as_posix(), contents)
        for filename in ("statistics.json", "quality_metrics.json", "dataset_manifest.json", "quality_report.md"):
            content = (EVIDENCE / filename).read_text(encoding="utf-8")
            if filename.endswith(".json"):
                content = json.dumps(scrub(json.loads(content)), ensure_ascii=False, indent=2)
            else:
                content = sanitize_text(content)
            archive.writestr("evidence/" + filename, content.encode("utf-8"))
        for path, name in ((evidence, "functional_results.json"), (environment, "training_environment.json")):
            archive.writestr("evidence/" + name, json.dumps(scrub(json.loads(path.read_text(encoding="utf-8"))), ensure_ascii=False, indent=2).encode("utf-8"))
    with zipfile.ZipFile(DEST) as archive:
        names = archive.namelist()
        missing = [name for name in REQUIRED if name not in names]
        invalid = archive.testzip()
        if missing or invalid or len(names) != len(set(names)):
            raise SystemExit(f"Invalid archive: missing={missing}, corrupt={invalid}")
    print(json.dumps({"file": str(DEST), "bytes": DEST.stat().st_size, "sha256": hashlib.sha256(DEST.read_bytes()).hexdigest(), "entries": len(names)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
