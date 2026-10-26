import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))
from evaluation import EVALUATION_OPTIONS, EVAL_PROFILES, resolve_selection, selection_fingerprint

spec = importlib.util.spec_from_file_location("make_eval_manifest", MODULE_DIR / "04_make_eval_manifest.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class EvaluationSelectionTest(unittest.TestCase):
    def test_catalog_and_gradual_presets(self):
        subjects = EVALUATION_OPTIONS["subjects"]
        self.assertEqual(len({subject["value"] for subject in subjects}), 119)
        self.assertEqual(sum(subject["benchmark"] == "ceval" for subject in subjects), 52)
        self.assertEqual(sum(subject["benchmark"] == "cmmlu" for subject in subjects), 67)
        totals = []
        previous = set()
        for mode in EVAL_PROFILES:
            selected, limit = resolve_selection(mode)
            self.assertTrue(previous <= set(selected))
            previous = set(selected)
            if limit is not None:
                totals.append(len(selected) * limit)
        self.assertEqual(totals, [10, 40, 90, 160, 250, 360])

    def test_custom_selection_validation_and_identity(self):
        selected = ["ceval:computer_network", "cmmlu:education"]
        self.assertEqual(resolve_selection("custom", selected * 2, 7), (selected, 7))
        self.assertEqual(resolve_selection("custom", selected, None, True), (selected, None))
        self.assertEqual(selection_fingerprint(selected, 7), selection_fingerprint(selected[::-1], 7))
        for subjects, limit in [([], 7), (["ceval:made_up"], 7), (selected, 0), (selected, 1.5), (selected, True), (selected, 10001)]:
            with self.subTest(subjects=subjects, limit=limit), self.assertRaises(ValueError):
                resolve_selection("custom", subjects, limit)

    def test_generated_config_exact_filter_and_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for limit in [7, None]:
                config = generator.write_limited_dataset_config(root, "ceval_gen", "custom", ["law"], limit)
                tree = ast.parse((root / "datasets/module4" / f"{config}.py").read_text(encoding="utf-8"))
                # 以小题库执行生成的过滤代码，无需加载模型或下载数据集。
                tree.body = [node for node in tree.body if not isinstance(node, (ast.ImportFrom, ast.With))]
                source = [
                    {"name": "law", "reader_cfg": {"test_split": "val", "test_range": "[0:2]"}},
                    {"name": "professional_law", "reader_cfg": {}},
                ]
                namespace = {"ceval_datasets": source}
                exec(compile(tree, "generated_dataset.py", "exec"), namespace)
                datasets = namespace["ceval_datasets"]
                self.assertEqual([dataset["name"] for dataset in datasets], ["law"])
                self.assertEqual(datasets[0]["reader_cfg"].get("test_range"), "[0:7]" if limit else None)
                self.assertEqual(source[0]["reader_cfg"]["test_range"], "[0:2]")
                with self.assertRaisesRegex(ValueError, "law"):
                    exec(compile(tree, "generated_dataset.py", "exec"), {"ceval_datasets": []})

    def test_cli_custom_subjects_limit_and_run_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifests = []
            for subjects, limit in [(["ceval:law"], "7"), (["ceval:law"], "8"), (["cmmlu:education"], "8"), (["ceval:law"], None)]:
                command = [sys.executable, str(MODULE_DIR / "04_make_eval_manifest.py"),
                           "--base-model", "local/test", "--variants", "--eval-mode", "custom",
                           "--subjects", *subjects, "--out-dir", str(root / "output"), "--workspace-dir", str(root / "workspace")]
                command += ["--samples-per-subject", limit] if limit else ["--all-questions"]
                subprocess.run(command, check=True, capture_output=True)
                manifest = json.loads((root / "output/eval_manifest.json").read_text(encoding="utf-8"))
                manifests.append(manifest)
                self.assertEqual(manifest["selected_subjects"], subjects)
                self.assertEqual(manifest["samples_per_subject"], int(limit) if limit else None)
                self.assertEqual(len(manifest["selected_benchmark_configs"]), 1)
            self.assertEqual(len({manifest["run_dir"] for manifest in manifests}), 4)
            self.assertEqual(len({manifest["config_dir"] for manifest in manifests}), 4)


if __name__ == "__main__":
    unittest.main()
