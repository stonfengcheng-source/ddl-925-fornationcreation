"""Exercise real baseline fitting and rejection of unsafe training inputs."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def run(tmp_path, rows):
    source = tmp_path / "input.jsonl"
    source.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    output = tmp_path / "results"
    result = subprocess.run([sys.executable, str(ROOT / "scripts/train_text_baseline.py"), "--input", str(source), "--output", str(output), "--version-id", "test-version", "--seed", "42", "--test-size", ".25"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
    return result, output


def labeled():
    return [{"sample_id":str(i), "text":f"{'数学' if i < 8 else '语文'} 教学内容 {i}", "label":"math" if i < 8 else "language"} for i in range(16)]


def test_training_creates_real_model_and_disjoint_holdout(tmp_path):
    result, output = run(tmp_path, labeled())
    assert result.returncode == 0, result.stderr
    assert (output / "model.joblib").stat().st_size > 0
    metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
    split = json.loads((output / "split.json").read_text(encoding="utf-8"))
    predictions = [json.loads(line) for line in (output / "predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert not set(split["train_ids"]) & set(split["test_ids"])
    assert len(predictions) == metrics["test_count"]
    assert metrics["accuracy"] == sum(item["actual"] == item["predicted"] for item in predictions) / len(predictions)


def test_missing_labels_are_not_inferred(tmp_path):
    rows = labeled(); rows[0].pop("label")
    result, output = run(tmp_path, rows)
    assert result.returncode != 0
    assert not (output / "model.joblib").exists()


def test_duplicate_text_is_rejected_before_split(tmp_path):
    rows = labeled(); rows[1]["text"] = rows[0]["text"]
    result, output = run(tmp_path, rows)
    assert result.returncode != 0
    assert not (output / "model.joblib").exists()
