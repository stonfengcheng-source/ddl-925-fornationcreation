"""Package source, synthetic labeled data and actual baseline training evidence."""
import hashlib
import json
import zipfile
from pathlib import Path
from create_review_package import ROOT, SECRET_RE, sanitize_text, scrub, source_files

DEST = ROOT / "deliverables/data-platform-product-v6.zip"
REQUIRED = ["frontend/package.json", "frontend/package-lock.json", "backend/requirements.txt", "backend/app/api/baseline.py",
    "backend/app/api/preproject_data.py", "frontend/src/pages/Module4/ExperimentsPage.tsx", "data_pipeline/pipeline.py",
    "configs/baseline-requirements.txt", "scripts/train_text_baseline.py", "scripts/init_baseline_env.ps1", "scripts/check_baseline_env.py",
    "scripts/baseline_http_acceptance.py", "scripts/start_demo.ps1", "scripts/stop_demo.ps1",
    "demo-datasets/governance-example.jsonl", "demo-datasets/governance-example.sha256",
    "demo-datasets/education-classification-synthetic.jsonl", "demo-datasets/education-classification-synthetic.sha256",
    "docs/product_v6_design.md", "docs/data_governance_acceptance.md", "docs/python_training_acceptance.md",
    "docs/frontend_visual_review.md", "docs/end_to_end_acceptance.md", "docs/known_issues.md", "evidence/baseline_acceptance.json", "evidence/baseline/model.joblib"]


def main():
    evidence_path = ROOT / "tmp/baseline-v13/acceptance_results.json"
    if not evidence_path.is_file(): raise SystemExit("Missing real baseline acceptance")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("result") != "BASELINE_TRAINING_PASS": raise SystemExit("Baseline training acceptance did not pass")
    experiment_id = evidence["experiment_id"]
    matches = list((ROOT / "tmp/baseline-v13").glob(f"*/storage/users/*/baseline_experiments/{experiment_id}"))
    if len(matches) != 1: raise SystemExit("Training artifacts not found uniquely")
    artifact_dir = matches[0]
    if hashlib.sha256((artifact_dir / "model.joblib").read_bytes()).hexdigest() != evidence["model_sha256"]: raise SystemExit("Model hash mismatch")
    files = [*source_files(), *[ROOT / f"demo-datasets/{name}" for name in ("governance-example.jsonl", "governance-example.sha256", "education-classification-synthetic.jsonl", "education-classification-synthetic.sha256")]]
    DEST.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(DEST, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            if relative.startswith("configs/module4/") and relative != "configs/module4/evaluation_options.json":
                continue  # Generated machine-specific training configs are rebuilt from source.
            content = path.read_bytes()
            if path.suffix.lower() == ".md": content = sanitize_text(content.decode("utf-8")).encode("utf-8")
            if SECRET_RE.search(content): raise SystemExit(f"Possible credential: {path.relative_to(ROOT)}")
            if path.suffix.lower() in {".py", ".ps1", ".bat", ".json", ".yaml", ".yml", ".ts", ".tsx", ".md"}:
                for private_path in (str(ROOT), str(Path.home())):
                    variants = {private_path, private_path.replace("\\", "/"), private_path.replace("\\", "\\\\")}
                    if any(value.encode("utf-8").lower() in content.lower() for value in variants): raise SystemExit(f"Local path in {relative}")
            archive.writestr(relative, content)
        archive.writestr("evidence/baseline_acceptance.json", json.dumps(scrub(evidence), ensure_ascii=False, indent=2).encode("utf-8"))
        previous = ROOT / "tmp/functional-r10/functional_results.json"
        if previous.is_file(): archive.writestr("evidence/functional_results.json", json.dumps(scrub(json.loads(previous.read_text(encoding="utf-8"))), ensure_ascii=False, indent=2).encode("utf-8"))
        for report_file, destination in ((ROOT / "tmp/baseline-v13/synthetic_governance_report.md", "evidence/synthetic_governance_report.md"), (ROOT / "tmp/functional-r10/educhat_governance_report.md", "evidence/educhat_governance_report.md")):
            if report_file.is_file(): archive.writestr(destination, sanitize_text(report_file.read_text(encoding="utf-8")).encode("utf-8"))
        # These artifacts contain only the explicitly synthetic classification corpus.
        for name in ("model.joblib", "metrics.json", "split.json", "predictions.jsonl", "errors.jsonl", "report.md", "config.json"):
            archive.writestr("evidence/baseline/" + name, (artifact_dir / name).read_bytes())
        log = (artifact_dir / "run.log").read_text(encoding="utf-8", errors="replace").splitlines()
        archive.writestr("evidence/baseline/execution.log", ("Command: python -u scripts/train_text_baseline.py --seed 42 --test-size 0.25\n" + "\n".join(line for line in log if not line.startswith("Execution command:")) + "\n").encode("utf-8"))
    with zipfile.ZipFile(DEST) as archive:
        names = archive.namelist()
        missing = [name for name in REQUIRED if name not in names]
        if missing or archive.testzip() or len(names) != len(set(names)): raise SystemExit(f"Invalid archive: {missing}")
    print(json.dumps({"file":str(DEST), "bytes":DEST.stat().st_size, "sha256":hashlib.sha256(DEST.read_bytes()).hexdigest(), "entries":len(names)}, ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
