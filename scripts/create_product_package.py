"""Package product source, safe examples and redacted acceptance evidence."""
import hashlib
import json
import zipfile

from create_review_package import ROOT, EVIDENCE, SECRET_RE, sanitize_text, scrub, source_files

DEST = ROOT / "deliverables/data-platform-product-integration-v4.zip"
REQUIRED = ["frontend/package.json", "frontend/package-lock.json", "backend/requirements.txt",
            "frontend/src/pages/Dashboard/ProductStart.tsx", "frontend/src/pages/Resources/index.tsx",
            "frontend/src/pages/Module4/index.tsx", "backend/app/api/preproject_data.py", "backend/app/api/module4.py",
            "data_pipeline/pipeline.py", "configs/preproject_pipeline.json", "scripts/start_demo.ps1", "scripts/stop_demo.ps1",
            "scripts/product_integration_check.py", "demo-datasets/governance-example.jsonl",
            "docs/product_architecture.md", "docs/navigation_reorganization.md", "docs/platform_resource_management.md",
            "docs/end_to_end_workflow.md", "docs/frontend_design_review.md", "docs/integration_test_report.md", "docs/known_issues.md",
            "evidence/product_results.json", "evidence/functional_results.json"]


def main():
    evidence = [(ROOT / "tmp/product-r11/product_results.json", "product_results.json"),
                (ROOT / "tmp/functional-r10/functional_results.json", "functional_results.json"),
                (ROOT / "tmp/module4-round10-env.json", "training_environment.json")]
    if any(not path.is_file() for path, _ in evidence):
        raise SystemExit("Missing recorded evidence")
    DEST.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(DEST, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in [*source_files(), ROOT / "demo-datasets/governance-example.jsonl"]:
            content = path.read_bytes()
            if path.suffix.lower() == ".md": content = sanitize_text(content.decode("utf-8")).encode("utf-8")
            if SECRET_RE.search(content): raise SystemExit(f"Possible credential in {path.relative_to(ROOT)}")
            archive.writestr(path.relative_to(ROOT).as_posix(), content)
        for path, name in evidence:
            archive.writestr("evidence/" + name, json.dumps(scrub(json.loads(path.read_text(encoding="utf-8"))), ensure_ascii=False, indent=2).encode("utf-8"))
        for name in ("statistics.json", "quality_metrics.json", "dataset_manifest.json", "quality_report.md"):
            content = (EVIDENCE / name).read_text(encoding="utf-8")
            content = json.dumps(scrub(json.loads(content)), ensure_ascii=False, indent=2) if name.endswith(".json") else sanitize_text(content)
            archive.writestr("evidence/" + name, content.encode("utf-8"))
    with zipfile.ZipFile(DEST) as archive:
        names = archive.namelist()
        missing = [name for name in REQUIRED if name not in names]
        if missing or archive.testzip() or len(names) != len(set(names)): raise SystemExit(f"Invalid archive: missing={missing}")
    print(json.dumps({"file": str(DEST), "bytes": DEST.stat().st_size, "sha256": hashlib.sha256(DEST.read_bytes()).hexdigest(), "entries": len(names)}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
