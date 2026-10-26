import ast
import csv
import json
import subprocess
import sys
import struct
import tempfile
import unittest
import importlib.util
from unittest.mock import patch
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

from common import EVAL_MODELS, TRAIN_VARIANTS, ensure_unique_ids, normalize_for_training, read_jsonl, training_schedule  # noqa: E402
from model_compat import legacy_compatible_config, lora_update_status, normalize_export_config  # noqa: E402
sys.path.insert(0, str(MODULE_DIR.parents[1] / "backend"))
from app.services.module4 import TRAINING_PYTHON, build_action_command  # noqa: E402


def write_jsonl(path: Path, rows) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


class Module4Test(unittest.TestCase):
    def test_one_step_training_keeps_nonzero_update_step(self):
        self.assertEqual(training_schedule(4, 1, 8, 1), {"estimated_optimizer_steps": 1, "warmup_steps": 0})
        self.assertEqual(training_schedule(2000, 1, 8, 3), {"estimated_optimizer_steps": 750, "warmup_steps": 75})

    def test_export_config_retains_legacy_rope_and_precision_without_touching_hardlinks(self):
        original = {"model_type": "qwen2", "dtype": "bfloat16", "rope_parameters": {"rope_theta": 1000000.0, "rope_type": "default"}}
        compatible = legacy_compatible_config(original)
        self.assertEqual(compatible["rope_theta"], 1000000.0)
        self.assertEqual(compatible["torch_dtype"], "bfloat16")
        self.assertNotIn("rope_theta", original)
        path = self.root / "config.json"
        path.write_text(json.dumps(original), encoding="utf-8")
        linked = self.root / "linked-config.json"
        import os
        os.link(path, linked)
        normalize_export_config(self.root)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), compatible)
        self.assertEqual(json.loads(linked.read_text(encoding="utf-8")), original)

    def test_lora_audit_detects_zero_update_adapter(self):
        path = self.root / "adapter.safetensors"
        header = json.dumps({"layer.lora_B.weight": {"dtype": "F32", "shape": [1], "data_offsets": [0, 4]}}).encode()
        for value, updated in [(0.0, False), (0.25, True)]:
            path.write_bytes(struct.pack("<Q", len(header)) + header + struct.pack("<f", value))
            self.assertEqual(lora_update_status(path)["has_update"], updated)

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.raw = self.root / "raw.jsonl"
        self.evaluated = self.root / "evaluated.jsonl"
        self.datajuicer = self.root / "datajuicer.jsonl"
        raw_rows = [
            {"id": "r1", "question": "重复问题", "answer": "重复答案"},
            {"id": "r2", "question": "重复问题", "answer": "重复答案"},
            {"id": "r3", "question": "问题3", "answer": "答案3"},
            {"id": "r4", "question": "问题4", "answer": "答案4"},
        ]
        evaluated_rows = [
            {
                "id": f"e{index}",
                "question": f"题目{index}",
                "input": f"上下文{index}",
                "answer": f"答案{index}",
                "subject": "数学" if index % 2 else "语文",
                "rule_pass": True,
                "decision": "keep",
                "quality_score": 0.9 - index * 0.01,
                "task_match_score": 0.8,
                "coverage_score": 0.7,
            }
            for index in range(1, 7)
        ]
        evaluated_rows.append(
            {
                "id": "e7",
                "question": "仅大模型高分样本",
                "answer": "答案7",
                "subject": "物理",
                "rule_pass": False,
                "decision": "drop",
                "quality_score": 0.99,
                "task_match_score": 0.1,
                "coverage_score": 0.1,
            }
        )
        write_jsonl(self.raw, raw_rows)
        write_jsonl(self.evaluated, evaluated_rows)
        write_jsonl(
            self.datajuicer,
            [
                {"id": f"d{index}", "question": f"Data-Juicer题目{index}", "answer": f"答案{index}"}
                for index in range(1, 7)
            ],
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_script(self, script_name, *args):
        command = [sys.executable, str(MODULE_DIR / script_name), *map(str, args)]
        return subprocess.run(command, check=True, text=True, capture_output=True)

    def test_normalize_preserves_context(self):
        row = normalize_for_training(
            {"id": "1", "instruction": "问题", "input": "上下文", "output": "答案"}
        )
        self.assertEqual(row["instruction"], "问题")
        self.assertEqual(row["input"], "上下文")

    def test_normalize_education_text_and_html(self):
        for text in [
            "题目：计算 1+1。\n答案：2\n解析：相加得到 2。",
            "<p>题目：计算 1+1。</p><p>答案：2</p><p>解析：相加得到 2。</p>",
            "题目:计算 1+1。\r\n答案:2\r\n解析:相加得到 2。",
        ]:
            with self.subTest(text=text):
                row = normalize_for_training({"sample_id": "edu-1", "raw_text": text})
                self.assertEqual(row["id"], "edu-1")
                self.assertEqual(row["instruction"], "计算 1+1。")
                self.assertEqual(row["input"], "")
                self.assertEqual(row["output"], "2\n解析：相加得到 2。")
        row = normalize_for_training({
            "sample_id": "edu-2", "raw_text": "<p>题目：a &lt; b 时，比较 a 和 b。</p><p>答案：a &lt; b</p>",
        })
        self.assertEqual(row["instruction"], "a < b 时，比较 a 和 b。")
        self.assertEqual(row["output"], "a < b")

    def test_education_text_does_not_override_explicit_qa_or_invent_missing_answer(self):
        row = normalize_for_training({
            "id": "explicit", "instruction": "原问题", "input": "上下文", "output": "原答案",
            "raw_text": "题目：其他问题\n答案：其他答案",
        })
        self.assertEqual((row["instruction"], row["input"], row["output"]), ("原问题", "上下文", "原答案"))
        for text in ["题目：只有问题", "题目：空答案\n答案：\n解析：不能充当答案"]:
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "问题/答案"):
                normalize_for_training({"sample_id": "incomplete", "raw_text": text})

    def test_sample_id_is_preserved_in_selection_audit(self):
        source = {"sample_id": "edu-1", "raw_text": "题目：问题\n答案：答案"}
        rows = ensure_unique_ids([source], "候选池")
        self.assertEqual(rows[0]["id"], "edu-1")
        self.assertNotIn("id", source)
        with self.assertRaisesRegex(ValueError, "重复 ID"):
            ensure_unique_ids([source, {"id": "edu-1"}], "候选池")

    def test_all_5000_education_candidates_and_dataset_generation(self):
        corpus = MODULE_DIR.parents[1] / "demo-datasets/education-synthetic/raw_5k.jsonl"
        rows = read_jsonl(corpus)
        self.assertEqual(len(rows), 5000)
        for row in rows:
            normalized = normalize_for_training(row)
            self.assertEqual(normalized["id"], row["sample_id"])
            self.assertTrue(normalized["instruction"])
            self.assertTrue(normalized["output"])
        # 同时覆盖使用 Schema v1 的上游处理结果，评分仅用于本测试的选择逻辑。
        evaluated = [{**row, "rule_pass": True, "quality_score": index / 10} for index, row in enumerate(rows[:10])]
        write_jsonl(self.evaluated, evaluated)
        write_jsonl(self.datajuicer, rows[:10])
        data_dir = self.root / "education_data"
        self.run_script("01_build_datasets.py", "--raw", corpus, "--evaluated", self.evaluated,
                        "--datajuicer", self.datajuicer, "--out-dir", data_dir, "--n", "4")
        self.run_script("02_validate_dataset.py", "--data-dir", data_dir, "--n", "4")
        audit = read_jsonl(data_dir / "selection_audit_4.jsonl")
        self.assertEqual(len(audit), 20)
        self.assertTrue(all(row["id"].startswith("edu-") for row in audit))
        self.assertTrue(all(row["subject"] != "unknown" for row in audit))

    def test_5000_raw_candidates_do_not_hide_insufficient_processed_inputs(self):
        project = MODULE_DIR.parents[1]
        data_dir = self.root / "insufficient_data"
        result = subprocess.run([
            sys.executable, str(MODULE_DIR / "01_build_datasets.py"),
            "--raw", str(project / "demo-datasets/education-synthetic/raw_5k.jsonl"),
            "--evaluated", str(self.evaluated),
            "--datajuicer", str(self.datajuicer),
            "--out-dir", str(data_dir), "--n", "100",
        ], check=False, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("原始候选 5000 条；质量评价 7 条；Data-Juicer 结果 6 条", result.stdout)
        for message in ["Rule 可用 6 条", "LLM-only 可用 7 条", "Data-Juicer 可用 6 条", "Ours 可用 6 条"]:
            self.assertIn(message, result.stderr)
        self.assertIn(self.evaluated.name, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(data_dir.exists())

    def test_raw_only_100_samples_validate_and_prepare_without_pending_groups(self):
        data_dir = self.root / "raw_only_data"
        corpus = MODULE_DIR.parents[1] / "demo-datasets/education-synthetic/raw_5k.jsonl"
        result = self.run_script("01_build_datasets.py", "--raw", corpus, "--out-dir", data_dir, "--n", "100")
        self.assertIn("[待接入] Rule", result.stdout)
        manifest = json.loads((data_dir / "dataset_manifest_100.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["variants"]), {"raw"})
        self.assertEqual(set(manifest["pending_variants"]), {"rule", "llm_only", "datajuicer", "ours"})
        self.assertIsNone(manifest["sources"]["evaluated"])
        self.assertFalse((data_dir / "ours_100.jsonl").exists())
        (data_dir / "ours_100.jsonl").write_text("not valid json", encoding="utf-8")
        self.run_script("02_validate_dataset.py", "--data-dir", data_dir, "--n", "100")
        report = json.loads((data_dir / "validation_report_100.json").read_text(encoding="utf-8"))
        self.assertTrue(report["passed"])
        self.assertEqual(set(report["variants"]), {"raw"})
        config_dir = self.root / "raw_only_configs"
        self.run_script("03_prepare_llamafactory.py", "--model", "local/test-model", "--data-dir", data_dir,
                        "--out-dir", config_dir, "--experiment-dir", self.root / "experiment", "--n", "100")
        training = json.loads((config_dir / "training_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(set(training["train_configs"]), {"raw"})
        self.assertEqual(set(training["merge_configs"]), {"raw"})
        self.assertFalse((config_dir / "ours_lora.yaml").exists())
        spec = importlib.util.spec_from_file_location("partial_training", MODULE_DIR / "07_run_llamafactory.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(sys, "argv", ["runner", "train", "--config-dir", str(config_dir)]), patch.object(module, "run_single") as run_single:
            module.main()
        run_single.assert_called_once_with("train", "raw", config_dir)

    def test_partial_evaluation_uses_only_base_and_raw(self):
        merged = self.root / "partial_models" / "raw"
        merged.mkdir(parents=True)
        (merged / "config.json").write_text('{"model_type":"qwen2"}', encoding="utf-8")
        (merged / "model.safetensors").write_bytes(b"test-weights")
        output = self.root / "partial_eval"
        workspace = self.root / "ascii_workspace"
        self.run_script("04_make_eval_manifest.py", "--base-model", "local/test-model", "--merged-dir", merged.parent,
                        "--out-dir", output, "--workspace-dir", workspace, "--variants", "raw")
        manifest_path = output / "eval_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["models"]), {"base", "raw"})
        self.assertEqual(set(manifest["commands"]), {"base", "raw"})
        for name, score in [("base", 40), ("raw", 42), ("ours", 99)]:
            results = Path(manifest["run_dir"]) / name / "20261025_120000" / "results"
            results.mkdir(parents=True)
            (results / "ceval-test.json").write_text(json.dumps({"accuracy": score}), encoding="utf-8")
        summary = output / "summary.csv"
        self.run_script("05_compare_results.py", "--workspace", workspace, "--manifest", manifest_path,
                        "--scores-output", output / "scores.csv", "--output", summary)
        with summary.open(encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual({row["model"] for row in rows}, {"base", "raw"})
        self.assertTrue(all(row["delta_score"] == "2.000000" for row in rows if row["model"] == "raw"))
        spec = importlib.util.spec_from_file_location("partial_evaluation", MODULE_DIR / "08_run_opencompass.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(sys, "argv", ["runner", "dry-run", "--manifest", str(manifest_path)]), \
             patch.object(module, "executable_from_env", return_value=Path("opencompass.exe")), \
             patch.object(module, "python_from_env", return_value=Path(sys.executable)), \
             patch.object(module, "check_tokenizer_compatibility"), \
             patch.object(module.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
            module.main()
        self.assertEqual(run.call_count, 3)  # 一次兼容检查，Base / Raw 各一次试运行。
        commands = [call.args[0] for call in run.call_args_list[1:]]
        self.assertEqual([command[2] for command in commands], ["module4_base_hf", "module4_raw_hf"])

    def test_optional_inputs_keep_rule_and_ours_pending_without_rule_fields(self):
        write_jsonl(self.evaluated, [{"sample_id": "e1", "raw_text": "题目：问题\n答案：答案", "quality_score": 0.9}])
        data_dir = self.root / "scored_only"
        self.run_script("01_build_datasets.py", "--raw", self.raw, "--evaluated", self.evaluated,
                        "--out-dir", data_dir, "--n", "1")
        manifest = json.loads((data_dir / "dataset_manifest_1.json").read_text(encoding="utf-8"))
        self.assertEqual(set(manifest["variants"]), {"raw", "llm_only"})
        self.assertIn("rule", manifest["pending_variants"])
        self.assertIn("ours", manifest["pending_variants"])
        self.run_script("02_validate_dataset.py", "--data-dir", data_dir, "--n", "1")

    def test_end_to_end_preparation(self):
        data_dir = self.root / "data"
        self.run_script(
            "01_build_datasets.py",
            "--raw", self.raw,
            "--evaluated", self.evaluated,
            "--datajuicer", self.datajuicer,
            "--out-dir", data_dir,
            "--n", "4",
            "--seed", "42",
        )
        for name in TRAIN_VARIANTS:
            path = data_dir / f"{name}_4.jsonl"
            self.assertTrue(path.exists())
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 4)
        llm_ids = {
            row["id"]
            for row in map(
                json.loads,
                (data_dir / "llm_only_4.jsonl").read_text(encoding="utf-8").splitlines(),
            )
        }
        rule_ids = {
            row["id"]
            for row in map(
                json.loads,
                (data_dir / "rule_4.jsonl").read_text(encoding="utf-8").splitlines(),
            )
        }
        self.assertIn("e7", llm_ids)
        self.assertNotIn("e7", rule_ids)
        manifest = json.loads((data_dir / "dataset_manifest_4.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["sample_count_per_variant"], 4)
        self.assertEqual(
            manifest["selection"]["llm_only"],
            "不使用规则，仅按 quality_score 单一总分 Top-K",
        )
        self.assertIn("Data-Juicer", manifest["selection"]["datajuicer"])
        result = self.run_script(
            "02_validate_dataset.py", "--data-dir", data_dir, "--n", "4"
        )
        self.assertIn("Raw 组保留", result.stdout)

        config_dir = self.root / "configs"
        experiment_dir = self.root / "experiment"
        self.run_script(
            "03_prepare_llamafactory.py",
            "--model", "local/test-model",
            "--data-dir", data_dir,
            "--out-dir", config_dir,
            "--experiment-dir", experiment_dir,
            "--n", "4",
        )
        self.assertTrue((config_dir / "llamafactory_data" / "dataset_info.json").exists())
        self.assertTrue((config_dir / "raw_merge.yaml").exists())
        self.assertTrue((config_dir / "llm_only_merge.yaml").exists())
        self.assertTrue((config_dir / "datajuicer_merge.yaml").exists())
        self.assertTrue((config_dir / "run_train.bat").exists())
        self.assertIn("07_run_llamafactory.py", (config_dir / "run_train.bat").read_text(encoding="utf-8"))
        schedule = json.loads((config_dir / "training_manifest.json").read_text(encoding="utf-8"))["schedule"]
        self.assertEqual(schedule, {"estimated_optimizer_steps": 3, "warmup_steps": 1})
        self.assertIn("warmup_steps: 1", (config_dir / "ours_lora.yaml").read_text(encoding="utf-8"))

    def test_result_summary_and_false_string_badcase(self):
        scores = self.root / "scores.csv"
        with scores.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["model", "benchmark", "score"])
            writer.writeheader()
            writer.writerows(
                [
                    {"model": "base", "benchmark": "ceval", "score": 50},
                    {"model": "ours", "benchmark": "ceval", "score": 54},
                ]
            )
        summary = self.root / "summary.csv"
        self.run_script("05_compare_results.py", "--input", scores, "--output", summary)
        with summary.open("r", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        ours = next(row for row in rows if row["model"] == "ours")
        self.assertEqual(ours["delta_score"], "4.000000")

        predictions = self.root / "predictions.jsonl"
        write_jsonl(
            predictions,
            [{"id": "q1", "prediction": "B", "reference": "A", "correct": "false"}],
        )
        badcases = self.root / "badcases.jsonl"
        self.run_script(
            "06_badcase_template.py", "--input", predictions, "--output", badcases
        )
        self.assertEqual(len(badcases.read_text(encoding="utf-8").splitlines()), 1)

    def test_auto_collects_latest_opencompass_results(self):
        workspace = self.root / "opencompass"
        for index, model in enumerate(EVAL_MODELS):
            result_dir = workspace / "runs" / model / "20260923_150000" / "results" / f"{model}_hf"
            result_dir.mkdir(parents=True)
            (result_dir / "ceval-computer_network.json").write_text(
                json.dumps({"accuracy": 50 + index}), encoding="utf-8"
            )
            (result_dir / "cmmlu-education.json").write_text(
                json.dumps({"accuracy": 60 + index}), encoding="utf-8"
            )
        scores = self.root / "auto_scores.csv"
        summary = self.root / "auto_summary.csv"
        result = self.run_script(
            "05_compare_results.py",
            "--workspace", workspace,
            "--scores-output", scores,
            "--output", summary,
        )
        self.assertIn("六个评测对象宏平均结果", result.stdout)
        with scores.open("r", encoding="utf-8-sig") as handle:
            score_rows = list(csv.DictReader(handle))
        self.assertEqual(len(score_rows), 12)
        with summary.open("r", encoding="utf-8-sig") as handle:
            summary_rows = list(csv.DictReader(handle))
        ours_overall = next(
            row for row in summary_rows
            if row["model"] == "ours" and row["benchmark"] == "overall_macro"
        )
        self.assertEqual(ours_overall["mean_score"], "60.000000")
        self.assertEqual(ours_overall["delta_score"], "5.000000")

    def test_result_collection_uses_new_protocol_without_old_scores(self):
        workspace = self.root / "workspace"
        run_root = workspace / "runs" / "protocol_v2"
        for model in EVAL_MODELS:
            for folder, score in [(workspace / "runs", 99), (run_root, 40)]:
                result = folder / model / "20261025_120000" / "results"
                result.mkdir(parents=True)
                (result / "ceval-test.json").write_text(json.dumps({"accuracy": score}), encoding="utf-8")
        manifest = self.root / "eval_manifest.json"
        manifest.write_text(json.dumps({"workspace_dir": str(workspace), "run_dir": str(run_root), "protocol_version": 2}), encoding="utf-8")
        output = self.root / "summary.csv"
        self.run_script("05_compare_results.py", "--workspace", workspace, "--manifest", manifest,
                        "--scores-output", self.root / "scores.csv", "--output", output)
        with output.open(encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        self.assertTrue(all(row["mean_score"] == "40.000000" for row in rows))

    def test_web_console_builds_safe_argument_lists(self):
        config = {
            "raw_path": str(self.raw),
            "evaluated_path": str(self.evaluated),
            "datajuicer_path": str(self.datajuicer),
            "sample_count": "4",
            "seed": "42",
        }
        command, label = build_action_command("build_data", config)
        self.assertIsInstance(command, list)
        self.assertEqual(command[0], str(TRAINING_PYTHON))
        self.assertIn("01_build_datasets.py", " ".join(command))
        self.assertIn("验证数据", label)
        self.assertIn("--datajuicer", command)
        with self.assertRaises(ValueError):
            build_action_command("arbitrary_command", config)
        with self.assertRaises(ValueError):
            build_action_command("train", {**config, "variant": "unknown"})

        repair, repair_label = build_action_command(
            "fix_eval_dependencies", {"opencompass_env": r"D:\opencompass_env"}
        )
        self.assertIn("09_fix_opencompass_dependencies.py", " ".join(repair))
        self.assertIn("--env-dir", repair)
        self.assertIn("修复", repair_label)

        compare, compare_label = build_action_command(
            "compare_results", {"eval_workspace": r"D:\module4_opencompass"}
        )
        self.assertIn("--workspace", compare)
        self.assertNotIn("--input", compare)
        self.assertIn("汇总", compare_label)

        with patch("app.services.module4.PROJECT_ROOT", self.root):
            score_command, score_label = build_action_command(
                "eval_score",
                {"eval_model": "all", "opencompass_env": r"D:\opencompass_env"},
            )
        self.assertIn("score", score_command)
        self.assertIn("仅重新评分", score_label)

    def test_eval_manifest_uses_ascii_workspace_and_model_mirrors(self):
        merged = self.root / "merged_models"
        for name in TRAIN_VARIANTS:
            model_dir = merged / name
            model_dir.mkdir(parents=True)
            (model_dir / "config.json").write_text(
                json.dumps({"model": name}), encoding="utf-8"
            )
            (model_dir / "model.safetensors").write_bytes(b"test-weights")
        output = self.root / "evaluation"
        workspace = self.root / "ascii_workspace"
        self.run_script(
            "04_make_eval_manifest.py",
            "--base-model", "Qwen/test-model",
            "--benchmarks", "ceval_gen",
            "--merged-dir", merged,
            "--out-dir", output,
            "--workspace-dir", workspace,
            "--batch-size", "1",
        )
        manifest = json.loads((output / "eval_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["protocol_version"], 3)
        self.assertEqual(Path(manifest["run_dir"]), workspace / "runs" / f"protocol_v3_quick_{manifest['selection_fingerprint']}_out512_bfloat16")
        self.assertEqual(manifest["max_out_len"], 512)
        for name, command in manifest["commands"].items():
            self.assertIn("--models", command)
            self.assertIn(f"module4_{name}_hf", command)
            self.assertNotIn("--hf-path", command)
            model_config = Path(manifest["config_dir"]) / "models" / "module4" / f"module4_{name}_hf.py"
            config_text = model_config.read_text(encoding="utf-8")
            self.assertIn(f"abbr='module4-{name.replace('_', '-')}-hf'", config_text)
            self.assertIn("tokenizer_path='Qwen/test-model'", config_text)
            self.assertIn("use_fast=False", config_text)
            self.assertIn("torch_dtype='bfloat16'", config_text)
            self.assertIn("generation_kwargs=dict(do_sample=False)", config_text)
            self.assertIn("max_out_len=512", config_text)
        self.assertEqual(Path(manifest["workspace_dir"]), workspace.resolve())
        for name in TRAIN_VARIANTS:
            self.assertTrue((workspace / "models" / name / "config.json").exists())
            command = manifest["commands"][name]
            self.assertIn(str(Path(manifest["run_dir"]) / name), command)
            model_config = (
                Path(manifest["config_dir"])
                / "models"
                / "module4"
                / f"module4_{name}_hf.py"
            )
            self.assertIn(
                str(workspace / "models" / name),
                [
                    node.value
                    for node in ast.walk(ast.parse(model_config.read_text(encoding="utf-8")))
                    if isinstance(node, ast.Constant) and isinstance(node.value, str)
                ],
            )

        command, _ = build_action_command(
            "make_eval_manifest",
            {"eval_workspace": str(workspace), "eval_batch_size": "1", "eval_mode": "quick"},
        )
        self.assertIn("--workspace-dir", command)
        self.assertIn(str(workspace), command)
        self.assertIn("--eval-mode", command)
        self.assertIn("quick", command)
        self.assertEqual(command[command.index("--max-out-len") + 1], "512")

        quick_output = self.root / "quick_evaluation"
        self.run_script(
            "04_make_eval_manifest.py",
            "--base-model", "Qwen/test-model",
            "--benchmarks", "ceval_gen", "cmmlu_gen",
            "--merged-dir", merged,
            "--out-dir", quick_output,
            "--workspace-dir", workspace,
            "--eval-mode", "quick",
            "--batch-size", "1",
        )
        quick_manifest = json.loads(
            (quick_output / "eval_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(quick_manifest["evaluation_mode"], "quick")
        self.assertEqual(quick_manifest["evaluation_profile"]["samples_per_subject"], 10)
        self.assertIn("--config-dir", quick_manifest["commands"]["base"])
        generated = Path(quick_manifest["config_dir"]) / "datasets" / "module4"
        self.assertTrue((generated / "module4_quick_ceval_gen.py").exists())
        self.assertTrue((generated / "module4_quick_cmmlu_gen.py").exists())

        with self.assertRaises(ValueError):
            build_action_command("make_eval_manifest", {"eval_mode": "unknown"})

    def test_output_budget_isolates_configurations_and_prediction_reuse(self):
        manifests = {}
        workspace = self.root / "isolated_workspace"
        for limit in (128, 512):
            output = self.root / f"evaluation_{limit}"
            self.run_script("04_make_eval_manifest.py", "--base-model", "local/test-model",
                            "--out-dir", output, "--workspace-dir", workspace, "--max-out-len", limit, "--variants")
            manifests[limit] = json.loads((output / "eval_manifest.json").read_text(encoding="utf-8"))
            config = Path(manifests[limit]["config_dir"]) / "models/module4/module4_base_hf.py"
            self.assertIn(f"max_out_len={limit}", config.read_text(encoding="utf-8"))
        self.assertNotEqual(manifests[128]["run_dir"], manifests[512]["run_dir"])
        self.assertNotEqual(manifests[128]["config_dir"], manifests[512]["config_dir"])
        old_predictions = Path(manifests[128]["run_dir"]) / "base/20261026_120000/predictions"
        old_predictions.mkdir(parents=True)
        (old_predictions / "answers.json").write_text("{}", encoding="utf-8")
        spec = importlib.util.spec_from_file_location("isolated_scoring", MODULE_DIR / "08_run_opencompass.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with self.assertRaises(FileNotFoundError):
            module.latest_prediction_timestamp(workspace, "base", Path(manifests[512]["run_dir"]))

    def test_eval_manifest_rejects_non_ascii_workspace(self):
        command = [
            sys.executable,
            str(MODULE_DIR / "04_make_eval_manifest.py"),
            "--base-model", "Qwen/test-model",
            "--out-dir", str(self.root / "evaluation"),
            "--workspace-dir", str(self.root / "中文目录"),
        ]
        result = subprocess.run(command, check=False, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("只能包含英文字母", result.stderr)


if __name__ == "__main__":
    unittest.main()
