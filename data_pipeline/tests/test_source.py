from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from unittest import mock
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from data_pipeline.source import DatasetViewerClient

TEMP_ROOT = Path(__file__).resolve().parents[2] / "tmp"
TEMP_ROOT.mkdir(exist_ok=True)


class FakeViewerClient(DatasetViewerClient):
    def _get_json(self, url: str, *, cache_key: str | None = None):
        if "/revision/" in url:
            return {"sha": "rev-1"}
        if "huggingface.co/api/datasets/" in url:
            return {"sha": "rev-1", "cardData": {"license": "cc-by-nc-4.0"}}
        query = parse_qs(urlparse(url).query)
        offset = int(query["offset"][0])
        length = int(query["length"][0])
        rows = []
        for index in range(offset, min(offset + length, 10)):
            row = {"data": [f"问题 {index}", f"答案 {index}"], "system_prompt": "助手"}
            rows.append({"row_idx": index, "row": row, "truncated_cells": []})
        return {"rows": rows, "num_rows_total": 10, "partial": False}


class SourceTests(unittest.TestCase):
    def test_huggingface_datasets_collector_uses_pinned_revision_and_schema(self):
        calls = {}

        class FakeIterable:
            def shuffle(self, *, seed, buffer_size):
                calls["shuffle"] = (seed, buffer_size)
                return self

            def take(self, count):
                return [{"sequence": [f"问题 {index}", f"答案 {index}"], "system_prompt": "助手"}
                        for index in range(count)]

        def fake_load_dataset(dataset_id, **kwargs):
            calls["dataset_id"] = dataset_id
            calls["load"] = kwargs
            return FakeIterable()

        fake_module = types.SimpleNamespace(__version__="5.0.1", load_dataset=fake_load_dataset)
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp:
            root = Path(temp)
            config = {"dataset_id": "org/data", "revision": "rev-1", "license": "cc-by-nc-4.0",
                      "config": "default", "split": "train", "expected_row_count": 10,
                      "sample_count": 2, "seed": 7, "collector": "huggingface_datasets",
                      "expected_fields": {"sequence": "list", "system_prompt": "str"},
                      "shuffle_buffer_size": 4}
            with mock.patch.dict(sys.modules, {"datasets": fake_module}):
                report = FakeViewerClient(config, root / "cache").sample(config, root / "raw.jsonl")
            rows = [json.loads(line) for line in (root / "raw.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(report["collector_version"], "5.0.1")
            self.assertEqual(report["sample_count"], 2)
            self.assertEqual(calls["load"]["revision"], "rev-1")
            self.assertTrue(calls["load"]["streaming"])
            self.assertEqual(calls["shuffle"], (7, 4))
            self.assertEqual(rows[1]["hf_stream_position"], 1)

    def test_sample_uses_pinned_license_verified_source_and_caches_manifest(self):
        config = {"dataset_id": "org/dataset", "revision": "rev-1", "license": "cc-by-nc-4.0",
                  "source_url": "https://huggingface.co/datasets/org/dataset", "config": "default", "split": "train",
                  "expected_row_count": 10, "sample_count": 5, "batch_size": 3, "seed": 8,
                  "max_page_requests": 8, "timeout_seconds": 1, "max_retries": 0, "min_interval_seconds": 0,
                  "expected_fields": {"data": "list", "system_prompt": "str"}}
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp:
            root = Path(temp)
            client = FakeViewerClient(config, root / "cache")
            report = client.sample(config, root / "raw.jsonl")
            rows = [json.loads(line) for line in (root / "raw.jsonl").read_text(encoding="utf-8").splitlines()]
            manifest = json.loads((root / "educhat_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(len(rows), 5)
            self.assertEqual(len({row["hf_row_idx"] for row in rows}), 5)
            self.assertTrue(report["revision_verified"])
            self.assertTrue(report["license_verified"])
            self.assertFalse(report["redistribution_authorized"])
            self.assertEqual(manifest["file_sha256"], report["file_sha256"])
            self.assertEqual(report["field_types"], {
                "data": ["list"], "hf_row_idx": ["int"], "system_prompt": ["str"],
            })
            self.assertEqual(report["source_field_mapping"]["output"], "data[last_assistant]")

    def test_sample_rejects_rows_that_do_not_match_expected_schema(self):
        config = {"dataset_id": "org/dataset", "revision": "rev-1", "license": "cc-by-nc-4.0",
                  "source_url": "https://huggingface.co/datasets/org/dataset", "config": "default", "split": "train",
                  "expected_row_count": 10, "sample_count": 2, "batch_size": 3, "seed": 8,
                  "max_page_requests": 8, "timeout_seconds": 1, "max_retries": 0, "min_interval_seconds": 0,
                  "expected_fields": {"data": "str"}}
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as temp:
            root = Path(temp)
            with self.assertRaisesRegex(RuntimeError, "字段结构与配置不符"):
                FakeViewerClient(config, root / "cache").sample(config, root / "raw.jsonl")
            self.assertFalse((root / "raw.jsonl").exists())

    def test_collect_rows_rejects_truncated_cells(self):
        sample_rows = {}
        truncated = set()
        DatasetViewerClient._collect_rows({"rows": [
            {"row_idx": 1, "row": {"sequence": ["q", "a"]}, "truncated_cells": ["sequence"]},
            {"row_idx": 2, "row": {"sequence": ["q2", "a2"]}, "truncated_cells": []},
        ]}, sample_rows, truncated)
        self.assertEqual(set(sample_rows), {2})
        self.assertEqual(truncated, {1})


if __name__ == "__main__":
    unittest.main()
