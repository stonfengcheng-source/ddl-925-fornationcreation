"""自动收集OpenCompass结果并生成统一比较表。"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from common import EVAL_MODELS

MODELS = EVAL_MODELS
METRIC_HINTS = ("accuracy", "acc", "score", "exact_match", "em", "f1")


def numeric_metrics(payload: Any, prefix: str = "") -> list[tuple[str, float]]:
    """从OpenCompass结果JSON中提取常见的数值评分字段。"""
    found: list[tuple[str, float]] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                if any(hint == str(key).lower() or hint in str(key).lower() for hint in METRIC_HINTS):
                    found.append((name, float(value)))
            elif isinstance(value, str):
                if any(hint == str(key).lower() or hint in str(key).lower() for hint in METRIC_HINTS):
                    try:
                        found.append((name, float(value.strip().rstrip("%"))))
                    except ValueError:
                        pass
            elif isinstance(value, dict):
                found.extend(numeric_metrics(value, name))
    return found


def primary_metric(payload: Any) -> tuple[str, float] | None:
    metrics = numeric_metrics(payload)
    if not metrics:
        return None
    priorities = ("accuracy", "acc", "score", "exact_match", "em", "f1")
    for preferred in priorities:
        for name, value in metrics:
            leaf = name.rsplit(".", 1)[-1].lower()
            if leaf == preferred:
                return preferred, value
    name, value = metrics[0]
    return name.rsplit(".", 1)[-1], value


def latest_result_dir(model_root: Path) -> Path | None:
    candidates: list[Path] = []
    if model_root.is_dir():
        for results_dir in model_root.glob("*/results"):
            if any(results_dir.rglob("*.json")):
                candidates.append(results_dir)
    if not candidates:
        return None
    return max(candidates, key=lambda path: (path.parent.name, path.stat().st_mtime))


def collect_opencompass_rows(workspace: Path, run_root: Path | None = None, models=MODELS) -> list[dict[str, str]]:
    runs_root = run_root or workspace / "runs"
    per_model: dict[str, dict[tuple[str, str], tuple[float, Path]]] = {}
    missing_models: list[str] = []

    for model in models:
        results_dir = latest_result_dir(runs_root / model)
        if results_dir is None:
            missing_models.append(model)
            continue
        scores: dict[tuple[str, str], tuple[float, Path]] = {}
        for result_file in sorted(results_dir.rglob("*.json")):
            try:
                payload = json.loads(result_file.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            selected = primary_metric(payload)
            if selected is None:
                continue
            metric, score = selected
            scores[(result_file.stem, metric)] = (score, result_file)
        if not scores:
            missing_models.append(model)
            continue
        per_model[model] = scores
        print(f"{model.upper()}：读取 {len(scores)} 个科目，目录 {results_dir.parent}")

    if missing_models:
        names = ", ".join(name.upper() for name in missing_models)
        raise FileNotFoundError(
            f"没有找到以下评测对象的已评分结果：{names}。"
            "如果summary表中的成绩全部是“-”，请先在网页点击“仅重新评分”，"
            f"评分完成后再汇总。检查目录：{runs_root}"
        )

    common = set.intersection(*(set(scores) for scores in per_model.values()))
    if not common:
        raise ValueError("当前评测对象没有名称与指标一致的共同科目，无法比较。")
    all_keys = set.union(*(set(scores) for scores in per_model.values()))
    excluded = all_keys.difference(common)
    if excluded:
        print(f"提示：有 {len(excluded)} 个科目未在当前评测对象中同时出现，已从比较中排除。")

    rows: list[dict[str, str]] = []
    for model in models:
        for benchmark, metric in sorted(common):
            score, source = per_model[model][(benchmark, metric)]
            rows.append({
                "model": model,
                "benchmark": benchmark,
                "metric": metric,
                "seed": "",
                "score": f"{score:.10g}",
                "source": str(source),
            })
    return rows


def write_scores(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["model", "benchmark", "metric", "seed", "score", "source"],
        )
        writer.writeheader()
        writer.writerows(rows)


def read_scores(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"手动分数表不存在：{path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_summary(rows: list[dict[str, str]]) -> list[dict[str, str | int]]:
    required = {"model", "benchmark", "score"}
    missing = required.difference(rows[0].keys() if rows else set())
    if missing:
        raise ValueError(f"分数表缺少列：{sorted(missing)}")

    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    family_scores: dict[tuple[str, str], list[float]] = defaultdict(list)
    overall_scores: dict[str, list[float]] = defaultdict(list)
    for line_number, row in enumerate(rows, 2):
        model = str(row.get("model", "")).strip().lower()
        benchmark = str(row.get("benchmark", "")).strip()
        metric = str(row.get("metric", "accuracy") or "accuracy").strip()
        if not model or not benchmark:
            raise ValueError(f"第 {line_number} 行 model 或 benchmark 为空")
        try:
            score = float(row["score"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"第 {line_number} 行 score 不是数字：{row.get('score')}") from exc
        grouped[(model, benchmark, metric)].append(score)
        lower = benchmark.lower()
        family = "ceval" if "ceval" in lower else "cmmlu" if "cmmlu" in lower else "other"
        family_scores[(model, family)].append(score)
        overall_scores[model].append(score)

    for (model, family), scores in family_scores.items():
        if family != "other":
            grouped[(model, f"{family}_macro", "macro_average")].append(statistics.mean(scores))
    for model, scores in overall_scores.items():
        grouped[(model, "overall_macro", "macro_average")].append(statistics.mean(scores))

    base_means = {
        (benchmark, metric): statistics.mean(scores)
        for (model, benchmark, metric), scores in grouped.items()
        if model == "base"
    }
    output_rows: list[dict[str, str | int]] = []
    for (model, benchmark, metric), scores in sorted(grouped.items()):
        mean_score = statistics.mean(scores)
        std_score = statistics.stdev(scores) if len(scores) > 1 else 0.0
        base_score = base_means.get((benchmark, metric))
        output_rows.append({
            "model": model,
            "benchmark": benchmark,
            "metric": metric,
            "runs": len(scores),
            "mean_score": f"{mean_score:.6f}",
            "std_score": f"{std_score:.6f}",
            "base_mean_score": "" if base_score is None else f"{base_score:.6f}",
            "delta_score": "" if base_score is None else f"{mean_score - base_score:.6f}",
        })
    return output_rows


def write_summary(path: Path, rows: list[dict[str, str | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "model", "benchmark", "metric", "runs", "mean_score", "std_score",
        "base_mean_score", "delta_score",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="可选：手动整理的统一分数CSV")
    parser.add_argument("--workspace", default=r"D:\module4_opencompass")
    parser.add_argument("--scores-output", default="experiments/module4/results/scores.csv")
    parser.add_argument("--output", default="experiments/module4/results/summary.csv")
    parser.add_argument("--manifest", default="experiments/module4/evaluation/eval_manifest.json")
    parser.add_argument("--require-manifest", action="store_true", help="平台汇总必须使用当前评测清单，避免读取旧实验结果")
    args = parser.parse_args()
    manifest = {}

    if args.input:
        rows = read_scores(Path(args.input))
        print(f"使用手动分数表：{args.input}")
    else:
        workspace = Path(args.workspace)
        print(f"正在自动收集当前评测对象的最新OpenCompass结果：{workspace / 'runs'}")
        run_root = None
        models = list(MODELS)
        manifest_path = Path(args.manifest)
        if args.require_manifest and not manifest_path.is_file():
            raise ValueError("尚未生成当前数据的评测配置和结果，请先完成对应模型的训练、合并与评测。")
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if args.require_manifest and manifest.get("protocol_version", 0) < 3:
                raise ValueError("当前评测配置未隔离旧的短输出预测。请重新生成评测配置、开始评测，再汇总结果。")
            if Path(manifest.get("workspace_dir", "")).resolve() == workspace.resolve():
                run_root = Path(manifest["run_dir"])
                if "commands" in manifest:
                    models = [name for name in MODELS if name in manifest["commands"]]
        if not models:
            raise ValueError("评测清单没有可汇总的模型")
        rows = collect_opencompass_rows(workspace, run_root, models)
        scores_output = Path(args.scores_output)
        write_scores(scores_output, rows)
        print(f"统一分数表已保存：{scores_output.resolve()}")

    output_rows = build_summary(rows)
    output_path = Path(args.output)
    write_summary(output_path, output_rows)
    training_path = Path("configs/module4/training_manifest.json")
    training = json.loads(training_path.read_text(encoding="utf-8")) if training_path.is_file() and not args.input else {}
    metadata = {
        "protocol_version": manifest.get("protocol_version"),
        "evaluation_mode": manifest.get("evaluation_mode"),
        "sample_count": training.get("sample_count"),
        "max_out_len": manifest.get("max_out_len"),
        "run_dir": manifest.get("run_dir"),
    }
    output_path.with_suffix(".metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    label = "六个评测对象" if len({row["model"] for row in rows}) == 6 else "本次评测对象"
    print(f"\n===== {label}宏平均结果 =====")
    for row in output_rows:
        if str(row["benchmark"]).endswith("_macro"):
            print(
                f"{row['model']:5} {row['benchmark']:14} "
                f"{row['mean_score']}  Δ={row['delta_score'] or 'N/A'}"
            )
    print(f"\n汇总结果已保存：{output_path.resolve()}")


if __name__ == "__main__":
    main()
