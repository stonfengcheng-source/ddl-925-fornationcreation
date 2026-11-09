"""Train a real supervised classification baseline on explicitly labeled data."""
import argparse
import hashlib
import json
import os
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

# A reused Conda base exposes its native runtime through Library/bin; this is
# needed even when the worker is launched without activating the shell.
_dll_handles = []
if os.name == "nt":
    for folder in (Path(sys.base_prefix) / "Library" / "bin", Path(sys.base_prefix) / "DLLs"):
        if folder.is_dir():
            _dll_handles.append(os.add_dll_directory(str(folder)))
            os.environ["PATH"] = str(folder) + os.pathsep + os.environ.get("PATH", "")

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--version-id", required=True)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--test-size", type=float, default=.25)
args = parser.parse_args()
start = time.monotonic()
output = Path(args.output)
output.mkdir(parents=True, exist_ok=True)
rows = [json.loads(line) for line in Path(args.input).read_text(encoding="utf-8").splitlines() if line.strip()]
if not rows or any(not isinstance(row.get("text"), str) or not row["text"].strip() or not isinstance(row.get("label"), str) or not row["label"].strip() or not row.get("sample_id") for row in rows):
    raise SystemExit("输入缺少文本、显式分类标签或样本标识。")
keys = ["".join(unicodedata.normalize("NFKC", row["text"]).casefold().split()) for row in rows]
if len(keys) != len(set(keys)):
    raise SystemExit("存在重复文本，请先去重，避免训练集和测试集泄漏。")
labels = [row["label"] for row in rows]
counts = Counter(labels)
if len(counts) < 2 or min(counts.values()) < 2:
    raise SystemExit("至少需要两个类别，每类至少两个已标注样本。")
print(f"Loaded {len(rows)} labeled records across {len(counts)} classes.", flush=True)
indices = list(range(len(rows)))
train, test = train_test_split(indices, test_size=args.test_size, random_state=args.seed, stratify=labels)
assert set(train).isdisjoint(test)
assert {keys[i] for i in train}.isdisjoint(keys[i] for i in test)
print(f"Stratified split: {len(train)} train, {len(test)} test.", flush=True)
pipeline = Pipeline([("tfidf", TfidfVectorizer(analyzer="char", ngram_range=(1, 3))),
                     ("classifier", LogisticRegression(max_iter=1000, random_state=args.seed))])
pipeline.fit([rows[i]["text"] for i in train], [labels[i] for i in train])
print("Model fit completed; evaluating held-out samples.", flush=True)
predictions = pipeline.predict([rows[i]["text"] for i in test]).tolist()
actual = [labels[i] for i in test]
classes = sorted(counts)
metrics = {"accuracy": float(accuracy_score(actual, predictions)), "macro_f1": float(f1_score(actual, predictions, average="macro", zero_division=0)),
           "confusion_matrix": confusion_matrix(actual, predictions, labels=classes).tolist(), "classes": classes,
           "train_count":len(train), "test_count":len(test), "dataset_count":len(rows), "duration_seconds":round(time.monotonic()-start, 3)}
split = {"train_ids":[rows[i]["sample_id"] for i in train], "test_ids":[rows[i]["sample_id"] for i in test],
         "seed":args.seed, "test_size":args.test_size, "source_sha256":hashlib.sha256(Path(args.input).read_bytes()).hexdigest()}
predicted_rows = [{"sample_id": rows[index]["sample_id"], "text":rows[index]["text"], "actual": truth, "predicted": pred}
                  for index, truth, pred in zip(test, actual, predictions)]
errors = [row for row in predicted_rows if row["actual"] != row["predicted"]]
config = {"algorithm":"tfidf_char_logistic_regression", "ngram_range":[1,3], "max_iter":1000, "seed":args.seed,
          "test_size":args.test_size, "data_version_id":args.version_id, "training_kind":"synthetic_supervised_classification_baseline"}
joblib.dump(pipeline, output / "model.joblib")
for name, value in (("metrics.json", metrics), ("split.json", split), ("config.json", config)):
    (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(output / "errors.jsonl").write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in errors), encoding="utf-8")
(output / "predictions.jsonl").write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in predicted_rows), encoding="utf-8")
(output / "report.md").write_text("# 轻量文本分类基线报告\n\n这是监督分类基线，并非大语言模型微调或 Proxy 结果。\n\n"
    f"- 训练样本：{len(train)}\n- 测试样本：{len(test)}\n- Accuracy：{metrics['accuracy']:.4f}\n- Macro-F1：{metrics['macro_f1']:.4f}\n- 错误样本：{len(errors)}\n", encoding="utf-8")
print("Model, metrics, split and report saved.", flush=True)
