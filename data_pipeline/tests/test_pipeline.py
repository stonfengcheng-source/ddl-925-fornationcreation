from __future__ import annotations

import copy
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from data_pipeline.deduplication import deduplicate
from data_pipeline.cli import main as cli_main
from data_pipeline.pipeline import PipelineCancelled, run_pipeline

TEMP_ROOT = Path(__file__).resolve().parents[2] / "tmp"
TEMP_ROOT.mkdir(exist_ok=True)


def base_config() -> dict:
    return {
        "schema_version": 1,
        "data_subset_id": "unit-test-subset",
        "task_id": "unit-test-task",
        "fixed_collected_at": "2026-01-02T03:04:05+00:00",
        "source": {"enabled": False, "dataset_id": "unit-test", "source_id": "fixture",
                   "source_url": "https://example.invalid/dataset", "license": "cc-by-nc-4.0",
                   "revision": "fixture-v1", "split": "test"},
        "license_policy": {"licenses_allowed_for_local_processing": ["cc-by-nc-4.0"]},
        "engineering_screens": {"enabled": ["schema_completeness", "text_integrity", "placeholder_content", "extreme_length"],
                                "placeholders": ["todo"], "max_chars": {"instruction": 1000, "output": 1000}},
        "deduplication": {"near_duplicate_enabled": False, "near_duplicate_hamming_distance": 3,
                          "near_duplicate_min_chars": 12},
        "privacy": {"text_fields": ["instruction", "input", "output", "system"],
                    "sensitive_fields": ["contact"], "patterns": {}, "replacements": {}},
        "quality": {"topic_keywords": {"mathematics": ["数学", "计算"]}, "reference_distribution": None,
                    "long_tail_share_threshold": 0.05, "stale_after_days": 730},
    }


class PipelineTests(unittest.TestCase):
    def test_cli_manifest_creates_user_attested_hash_and_sample_ids(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp:
            input_file = Path(temp) / "local.jsonl"
            input_file.write_text(json.dumps({"id": "source-1", "sequence": ["问题", "答案"]}, ensure_ascii=False) + "\n", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli_main(["manifest", "--input", str(input_file), "--dataset-id", "org/data",
                                 "--source-url", "https://example.invalid/data", "--license", "cc-by-nc-4.0",
                                 "--revision", "rev-1", "--split", "train"])
            manifest = json.loads(input_file.with_name("educhat_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(code, 0)
            self.assertEqual(manifest["sample_count"], 1)
            self.assertEqual(manifest["source_record_ids"], ["source-1"])
            self.assertEqual(len(manifest["sample_ids"]), 1)
            self.assertFalse(manifest["official_revision_verified"])

    def test_cancel_request_stops_before_outputs_are_written(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp:
            root = Path(temp)
            input_file = root / "source.jsonl"
            input_file.write_text(json.dumps({"instruction": "问题", "output": "答案"}, ensure_ascii=False) + "\n", encoding="utf-8")
            with self.assertRaises(PipelineCancelled):
                run_pipeline(input_path=input_file, output_dir=root / "cancelled", config=base_config(),
                             cancel_check=lambda: True)
            self.assertFalse((root / "cancelled" / "processed.jsonl").exists())

    def test_multiturn_sequence_preserves_context_and_rejects_incomplete_turn(self):
        rows = [
            {"id": "complete", "sequence": ["第一问", "第一答", "追问", "最终回答"], "system_prompt": "system"},
            {"id": "incomplete", "sequence": ["第一问", "第一答", "未回答的追问"], "system_prompt": "system"},
        ]
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp:
            root = Path(temp)
            input_file = root / "source.jsonl"
            input_file.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
            result = run_pipeline(input_path=input_file, output_dir=root / "run", config=base_config())
            output = json.loads((root / "run" / "qualified.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(output["instruction"], "追问")
            self.assertEqual(output["output"], "最终回答")
            self.assertIn("第一问", output["input"])
            self.assertIn("第一答", output["input"])
            self.assertEqual(output["system"], "system")
            self.assertEqual(result["statistics"]["drop_count"], 1)

    def test_educhat_data_field_preserves_multiturn_context_and_quarantines_incomplete_pair(self):
        rows = [
            {"sample_id": "official-row-10", "hf_row_idx": 10,
             "data": ["第一问", "第一答", "追问", "最终回答"], "system_prompt": "系统提示"},
            {"sample_id": "official-row-11", "hf_row_idx": 11,
             "data": ["第一问", "第一答", "未回答的追问"], "system_prompt": "系统提示"},
        ]
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp:
            root = Path(temp)
            input_file = root / "source.jsonl"
            input_file.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
            result = run_pipeline(input_path=input_file, output_dir=root / "run", config=base_config())
            output = json.loads((root / "run" / "qualified.jsonl").read_text(encoding="utf-8"))
            issues = [json.loads(line) for line in (root / "run" / "issue_samples.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(output["instruction"], "追问")
            self.assertEqual(output["output"], "最终回答")
            self.assertIn("第一问", output["input"])
            self.assertEqual(output["system"], "系统提示")
            self.assertEqual(output["source_field_mapping"]["output"], "data[last_assistant]")
            self.assertEqual(result["statistics"]["drop_count"], 1)
            self.assertIn("incomplete_conversation:data", issues[0]["reasons"])

    def test_json_array_import_and_manifest_hash_verification(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp:
            root = Path(temp)
            input_file = root / "source.json"
            input_file.write_text(json.dumps([{"id": "row-1", "sequence": ["问题", "答案"],
                                               "system_prompt": "system"}], ensure_ascii=False), encoding="utf-8")
            import hashlib
            manifest = root / "educhat_manifest.json"
            manifest.write_text(json.dumps({"dataset_id": "org/data", "revision": "rev-1", "split": "train",
                                            "license": "cc-by-nc-4.0", "source_url": "https://example.invalid",
                                            "file": input_file.name,
                                            "file_sha256": hashlib.sha256(input_file.read_bytes()).hexdigest(),
                                            "revision_verified": False, "license_verified": False}), encoding="utf-8")
            result = run_pipeline(input_path=input_file, output_dir=root / "run", config=base_config())
            self.assertEqual(result["statistics"]["raw_sample_count"], 1)
            self.assertEqual(result["statistics"]["input_format"], "json")
            output = json.loads((root / "run" / "processed.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(output["source_record_id"], "row-1")
            saved_manifest = json.loads((root / "run" / "dataset_manifest.json").read_text(encoding="utf-8"))
            self.assertTrue(saved_manifest["source_fetch_manifest"]["local_file_hash_verified"])
            self.assertFalse(saved_manifest["source_revision_verified"])
            self.assertFalse(saved_manifest["usage_boundary"]["release_eligible"])
            manifest.write_text(json.dumps({"dataset_id": "org/data", "file": input_file.name,
                                            "file_sha256": "0" * 64}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                run_pipeline(input_path=input_file, output_dir=root / "bad", config=base_config())

    def test_end_to_end_masks_deduplicates_and_exports_traceable_records(self):
        rows = [
            {"sample_id": "s1", "instruction": "<p>请讲解数学</p>",
             "output": "联系电话 13800138000，邮箱 abc@example.com。"},
            {"sample_id": "s2", "instruction": "请讲解数学", "output": "联系电话 13800138000，邮箱 abc@example.com。"},
            {"sample_id": "s3", "instruction": "请讲解数学！", "output": "联系电话13800138000，邮箱abc@example.com。"},
            {"sample_id": "s4", "instruction": "请说明计算方法并分步推导。", "output": "先列出已知条件，再逐步计算并核对结果。"},
        ]
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp:
            root = Path(temp)
            input_file = root / "source.jsonl"
            with input_file.open("w", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.write("{not-json}\n")
            result = run_pipeline(input_path=input_file, output_dir=root / "run", config=base_config())

            stats = result["statistics"]
            self.assertEqual(stats["raw_sample_count"], 4)
            self.assertEqual(stats["parse_error_count"], 1)
            self.assertEqual(stats["exact_duplicate_count"], 1)
            self.assertEqual(stats["normalized_duplicate_count"], 1)
            self.assertEqual(stats["privacy_hit_count"], stats["privacy_masked_count"])
            self.assertGreater(stats["privacy_masked_count"], 0)
            self.assertEqual(stats["final_retained_count"], 2)

            output = (root / "run" / "processed.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(output), 4)
            qualified = [json.loads(line) for line in (root / "run" / "qualified.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(qualified), 2)
            self.assertTrue(all(row["processing_status"] == "keep" for row in qualified))
            traceable = json.loads(output[0])
            self.assertEqual(len(traceable["cleaning_audit"]["before_hash"]), 64)
            self.assertEqual(len(traceable["cleaning_audit"]["after_hash"]), 64)
            self.assertEqual(traceable["privacy_audit"]["engine"], "privacy-patterns-v1")
            self.assertTrue(traceable["privacy_audit"]["rules"])
            self.assertIn("[PHONE]", "\n".join(output))
            self.assertIn("[EMAIL]", "\n".join(output))
            self.assertNotIn("13800138000", "\n".join(output))
            self.assertNotIn("abc@example.com", "\n".join(output))
            self.assertTrue((root / "run" / "dataset_manifest.json").is_file())
            self.assertTrue((root / "run" / "quality_report.md").is_file())
            self.assertTrue((root / "run" / "review_queue.jsonl").is_file())

            issues = (root / "run" / "issue_samples.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("13800138000", issues)
            self.assertNotIn("abc@example.com", issues)
            unbiasedness = result["quality"]["metrics"]["unbiasedness"]["reference_distribution_difference"]
            self.assertIsNone(unbiasedness["value"])
            self.assertEqual(unbiasedness["status"], "not_measurable")
            self.assertEqual(unbiasedness["dimension"], "unbiasedness")
            consistency = result["quality"]["metrics"]["consistency"]
            self.assertIsNone(consistency["cross_modal_match_rate"]["value"])
            self.assertIsNone(consistency["reviewer_agreement_rate"]["value"])
            self.assertTrue(consistency["reviewer_agreement_rate"]["not_measurable_reason"])
            completeness = result["quality"]["metrics"]["completeness"]["required_field_completeness_rate"]
            self.assertEqual(completeness["formula"], "samples with all required fields / samples checked")

    def test_fixed_input_and_config_produce_same_processed_jsonl(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp:
            root = Path(temp)
            input_file = root / "source.jsonl"
            input_file.write_text(json.dumps({"sample_id": "stable", "instruction": "说明数学题", "output": "先计算，再核对。"}, ensure_ascii=False) + "\n", encoding="utf-8")
            config = base_config()
            run_pipeline(input_path=input_file, output_dir=root / "first", config=copy.deepcopy(config))
            run_pipeline(input_path=input_file, output_dir=root / "second", config=copy.deepcopy(config))
            self.assertEqual((root / "first" / "processed.jsonl").read_bytes(), (root / "second" / "processed.jsonl").read_bytes())

    def test_unknown_license_quarantines_rows(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp:
            root = Path(temp)
            input_file = root / "source.jsonl"
            input_file.write_text(json.dumps({"sample_id": "unlicensed", "instruction": "说明问题", "output": "回答。"}, ensure_ascii=False) + "\n", encoding="utf-8")
            config = base_config()
            config["source"]["license"] = "unknown"
            result = run_pipeline(input_path=input_file, output_dir=root / "run", config=config)
            self.assertEqual(result["statistics"]["final_retained_count"], 0)
            self.assertEqual(result["statistics"]["quarantine_count"], 1)
            self.assertIn("license_not_cleared_for_local_processing", (root / "run" / "issue_samples.jsonl").read_text(encoding="utf-8"))

    def test_near_duplicates_are_reviewed_not_dropped(self):
        records = []
        for sample_id, suffix in (("a", ""), ("b", "啊")):
            records.append({"sample_id": sample_id, "instruction": "请详细讲解这道数学题并说明每一步的推理过程。",
                            "input": "", "output": "先列出已知条件，再逐步计算并核对最终结果。" + suffix,
                            "raw_record_sha256": sample_id, "processing_status": "keep", "processing_reasons": [],
                            "near_duplicate_sample_ids": []})
        report = deduplicate(records, {"near_duplicate_enabled": True, "near_duplicate_hamming_distance": 64,
                                       "near_duplicate_min_chars": 12})
        self.assertGreaterEqual(report["near_duplicate_sample_count"], 1)
        self.assertTrue(all(row["processing_status"] == "review" for row in records))
        self.assertTrue(all(row["duplicate_type"] == "near_approximate" for row in records))
        self.assertTrue(all(row["duplicate_cluster_id"] == "a" for row in records))
        self.assertEqual(report["near_duplicate_policy"], "flag_for_review; never_auto_drop")
        self.assertEqual(report["parameters"]["hamming_distance_threshold"], 64)


if __name__ == "__main__":
    unittest.main()
