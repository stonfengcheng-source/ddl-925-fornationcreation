"""Package default demo code, synthetic fixture and non-sensitive execution evidence."""
import hashlib
import json
import zipfile
from create_review_package import ROOT, SECRET_RE, sanitize_text, scrub, source_files

DEST = ROOT / "deliverables/data-platform-demo-ready-v5.zip"
REQUIRED = ["frontend/package.json", "frontend/package-lock.json", "backend/requirements.txt", "data_pipeline/pipeline.py",
            "backend/app/api/preproject_data.py", "frontend/src/pages/Dashboard/ProductStart.tsx", "frontend/src/pages/PreprojectData/pages/QualityPage.tsx",
            "frontend/src/pages/Module4/index.tsx", "configs/preproject_pipeline.json", "demo-datasets/governance-example.jsonl",
            "demo-datasets/governance-example.sha256", "scripts/generate_governance_example.py", "scripts/start_demo.ps1", "scripts/stop_demo.ps1",
            "scripts/default_demo_acceptance.py", "docs/demo_first_run.md", "docs/demo_workflow.md", "docs/frontend_visual_redesign.md",
            "docs/demo_acceptance_report.md", "docs/known_issues.md", "evidence/default_demo_acceptance.json", "evidence/functional_results.json"]


def main():
    evidence = [(ROOT / "tmp/default-demo-v12/acceptance_results.json", "default_demo_acceptance.json"),
                (ROOT / "tmp/functional-r10/functional_results.json", "functional_results.json")]
    if any(not path.is_file() for path, _ in evidence): raise SystemExit("Missing actual acceptance evidence")
    if json.loads(evidence[0][0].read_text(encoding="utf-8")).get("result") != "DEFAULT_DEMO_PASS": raise SystemExit("Default demonstration has not passed")
    DEST.parent.mkdir(parents=True, exist_ok=True)
    files = [*source_files(), ROOT / "demo-datasets/governance-example.jsonl", ROOT / "demo-datasets/governance-example.sha256"]
    with zipfile.ZipFile(DEST, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            data = path.read_bytes()
            if path.suffix.lower() == ".md": data = sanitize_text(data.decode("utf-8")).encode("utf-8")
            if SECRET_RE.search(data): raise SystemExit(f"Possible credential in {path.relative_to(ROOT)}")
            archive.writestr(path.relative_to(ROOT).as_posix(), data)
        for path, name in evidence:
            archive.writestr("evidence/" + name, json.dumps(scrub(json.loads(path.read_text(encoding="utf-8"))), ensure_ascii=False, indent=2).encode("utf-8"))
    with zipfile.ZipFile(DEST) as archive:
        names = archive.namelist()
        missing = [name for name in REQUIRED if name not in names]
        if missing or archive.testzip() or len(names) != len(set(names)): raise SystemExit(f"Invalid package: {missing}")
    print(json.dumps({"file": str(DEST), "bytes": DEST.stat().st_size, "sha256": hashlib.sha256(DEST.read_bytes()).hexdigest(), "entries": len(names)}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
