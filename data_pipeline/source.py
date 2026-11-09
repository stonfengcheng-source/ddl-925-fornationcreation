"""受限重试、缓存与断点续取的 Hugging Face Dataset Viewer 采集器。"""
from __future__ import annotations

import hashlib
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


class SourceError(RuntimeError):
    pass


class DatasetViewerClient:
    def __init__(self, config: dict[str, Any], cache_dir: str | Path):
        self.config = config
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = float(config.get("timeout_seconds", 30))
        self.retries = int(config.get("max_retries", 4))
        self.backoff = float(config.get("retry_backoff_seconds", 1.0))
        self.min_interval = float(config.get("min_interval_seconds", 0.5))
        self._last_request = 0.0
        self._request_count = 0
        self._cache_hits = 0
        self.request_log: list[dict[str, Any]] = []

    def _get_json(self, url: str, *, cache_key: str | None = None) -> dict[str, Any]:
        cache_path = self.cache_dir / f"{cache_key}.json" if cache_key else None
        if cache_path and cache_path.is_file():
            try:
                self._cache_hits += 1
                self.request_log.append({"timestamp": datetime.now(timezone.utc).isoformat(),
                                         "endpoint": urlsplit(url).path, "cache_key": cache_key,
                                         "result": "cache_hit", "attempts": 0})
                return json.loads(cache_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                cache_path.unlink(missing_ok=True)
        request_started = time.monotonic()
        for attempt in range(self.retries + 1):
            wait = self.min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            request = Request(url, headers={"User-Agent": "preproject-data-pipeline/0.1 (research data retrieval)"})
            self._last_request = time.monotonic()
            self._request_count += 1
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    payload = response.read()
                    status = getattr(response, "status", 200)
                result = json.loads(payload.decode("utf-8"))
                if not isinstance(result, dict):
                    raise SourceError("官方接口返回内容不是 JSON 对象。")
                if cache_path:
                    temporary = cache_path.with_suffix(".tmp")
                    temporary.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
                    temporary.replace(cache_path)
                self.request_log.append({"timestamp": datetime.now(timezone.utc).isoformat(),
                                         "endpoint": urlsplit(url).path, "cache_key": cache_key,
                                         "result": "success", "http_status": status, "attempts": attempt + 1,
                                         "elapsed_seconds": round(time.monotonic() - request_started, 6)})
                return result
            except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                code = getattr(exc, "code", None)
                self.request_log.append({"timestamp": datetime.now(timezone.utc).isoformat(),
                                         "endpoint": urlsplit(url).path, "cache_key": cache_key,
                                         "result": "retry" if attempt < self.retries else "failed",
                                         "http_status": code, "attempt": attempt + 1,
                                         "error_type": type(exc).__name__})
                if attempt >= self.retries:
                    detail = f"HTTP {code}" if code else type(exc).__name__
                    raise SourceError(f"Hugging Face 数据接口请求失败（{detail}，重试 {self.retries} 次）。") from None
                time.sleep(min(self.backoff * (2 ** attempt), 30.0))
        raise SourceError("数据接口请求未完成。")

    def verify(self, source: dict[str, Any]) -> dict[str, Any]:
        dataset_id = str(source["dataset_id"])
        revision = str(source["revision"])
        base = str(source.get("hub_api_base", "https://huggingface.co/api/datasets")).rstrip("/")
        encoded_id = "/".join(__import__("urllib.parse", fromlist=["quote"]).quote(part, safe="") for part in dataset_id.split("/"))
        details = self._get_json(f"{base}/{encoded_id}")
        current_revision = str(details.get("sha") or "")
        card = details.get("cardData") if isinstance(details.get("cardData"), dict) else {}
        current_license = str(card.get("license") or "unknown").casefold()
        expected_license = str(source.get("license") or "unknown").casefold()
        if not current_revision:
            raise SourceError("无法从官方数据集 API 读取当前 revision；为避免版本漂移，停止采集。")
        if current_revision != revision:
            raise SourceError(f"数据集当前 revision 与配置不一致（expected={revision}, current={current_revision}）；请先核对版本并更新配置。")
        if current_license == "unknown" or current_license != expected_license:
            raise SourceError(f"数据集许可与配置不一致或未声明（expected={expected_license}, current={current_license}）；停止采集。")
        revision_endpoint = f"{base}/{encoded_id}/revision/{revision}"
        revision_details = self._get_json(revision_endpoint)
        if str(revision_details.get("sha") or "") != revision:
            raise SourceError("指定 revision 未通过官方 API 核验。")
        return {
            "dataset_id": dataset_id,
            "current_revision": current_revision,
            "revision_verified": True,
            "license": current_license,
            "license_verified": True,
            "source_url": source.get("source_url"),
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

    def sample(self, source: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
        verification = self.verify(source)
        if source.get("collector") == "huggingface_datasets":
            return self._sample_with_hf_datasets(source, output_path, verification)
        api_base = str(source.get("rows_api_base", "https://datasets-server.huggingface.co/rows")).rstrip("/")
        dataset_id = str(source["dataset_id"])
        config_name = str(source.get("config", "default"))
        split = str(source.get("split", "train"))
        count = int(source.get("sample_count", 5000))
        batch = min(int(source.get("batch_size", 100)), 100)
        seed = int(source.get("seed", 20260924))
        expected_rows = int(source.get("expected_row_count", 0))
        if count < 1 or batch < 1:
            raise SourceError("sample_count 和 batch_size 必须为正数。")
        state_material = f"{dataset_id}|{verification['current_revision']}|{config_name}|{split}|{seed}|{count}|{batch}"
        state_hash = hashlib.sha256(state_material.encode("utf-8")).hexdigest()
        state_path = self.cache_dir / f"sample_state_{state_hash[:20]}.json"
        state: dict[str, Any] = {}
        if state_path.is_file():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                state = {}
        rng = random.Random(seed)
        offsets = list(state.get("attempted_offsets", []))
        draw_count = int(state.get("draw_count", len(offsets)))
        for _ in range(draw_count):
            rng.randrange(0, max(1, expected_rows - batch + 1))
        sample_rows: dict[int, dict[str, Any]] = {}
        truncated_rows: set[int] = set()
        for offset in offsets:
            page = self._get_page(api_base, dataset_id, config_name, split, int(offset), batch, verification["current_revision"])
            self._validate_page_total(page, expected_rows)
            self._collect_rows(page, sample_rows, truncated_rows)
        max_requests = int(source.get("max_page_requests", max(100, (count // batch + 1) * 10)))
        attempts = draw_count
        while len(sample_rows) < count and len(offsets) < max_requests and attempts < max_requests * 2:
            offset = rng.randrange(0, max(1, expected_rows - batch + 1))
            attempts += 1
            if offset in offsets:
                state = {"seed": seed, "attempted_offsets": offsets, "draw_count": attempts,
                         "usable_row_count": len(sample_rows), "truncated_row_count": len(truncated_rows),
                         "revision": verification["current_revision"]}
                state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
                continue
            offsets.append(offset)
            page = self._get_page(api_base, dataset_id, config_name, split, offset, batch, verification["current_revision"])
            self._validate_page_total(page, expected_rows)
            self._collect_rows(page, sample_rows, truncated_rows)
            state = {"seed": seed, "attempted_offsets": offsets, "draw_count": attempts,
                     "usable_row_count": len(sample_rows),
                     "truncated_row_count": len(truncated_rows), "revision": verification["current_revision"]}
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        if len(sample_rows) < count:
            raise SourceError(f"达到 page request 上限后仅取得 {len(sample_rows)}/{count} 条完整唯一样本；缓存已保留，可恢复续取。")
        # Deterministically sample across the candidate rows fetched at random offsets.
        selected_indices = sorted(rng.sample(sorted(sample_rows), count))
        selected = [sample_rows[index] for index in selected_indices]
        field_types: dict[str, set[str]] = {}
        for row in selected:
            for name, value in row.items():
                field_types.setdefault(str(name), set()).add(type(value).__name__)
        expected_fields = source.get("expected_fields", {"data": "list", "system_prompt": "str"})
        for name, expected in expected_fields.items():
            observed = field_types.get(str(name), set())
            type_ok = (expected == "list" and bool(observed) and all(kind in {"list", "tuple"} for kind in observed)) or (
                expected == "str" and bool(observed) and all(kind == "str" for kind in observed)
            )
            if not type_ok:
                raise SourceError(f"字段结构与配置不符：{name} expected={expected}, observed={sorted(observed)}")
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            raise SourceError(f"原始输出已存在，为保护原始数据未覆盖：{output_path}")
        collected_at = datetime.now(timezone.utc).isoformat()
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            sample_ids: list[str] = []
            for row_index, row in zip(selected_indices, selected):
                row["collected_at"] = collected_at
                material = "\x1f".join((dataset_id, verification["current_revision"], split, str(row_index)))
                row["sample_id"] = "edu_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
                sample_ids.append(row["sample_id"])
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        temporary.replace(output_path)
        digest = hashlib.sha256(output_path.read_bytes()).hexdigest()
        report = {
            **verification,
            "revision": verification["current_revision"],
            "config": config_name,
            "split": split,
            "expected_row_count": expected_rows,
            "sample_count": len(selected),
            "sample_ids": sample_ids,
            "source_record_ids": [str(index) for index in selected_indices],
            "field_types": {name: sorted(values) for name, values in sorted(field_types.items())},
            "source_field_mapping": {
                "instruction": "data[last_user]", "input": "data[history]",
                "output": "data[last_assistant]", "system": "system_prompt",
            },
            "seed": seed,
            "sampling_method": "seeded random row offsets; fetch up to 100 rows per request; unique hf_row_idx; truncated cells rejected",
            "attempted_offsets": offsets,
            "truncated_row_count": len(truncated_rows),
            "cache_hits": self._cache_hits,
            "http_request_count": self._request_count,
            "file": str(output_path.resolve()),
            "file_sha256": digest,
            "license_boundary": "CC BY-NC data; local non-commercial research only unless additional permission is obtained.",
            "redistribution_authorized": False,
        }
        report_path = output_path.with_name("educhat_manifest.json")
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log_path = output_path.with_name("collection_log.jsonl")
        with log_path.open("w", encoding="utf-8", newline="\n") as handle:
            for entry in self.request_log:
                handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        report["collection_log"] = str(log_path.resolve())
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report

    def _sample_with_hf_datasets(
        self, source: dict[str, Any], output_path: str | Path, verification: dict[str, Any]
    ) -> dict[str, Any]:
        """通过 Hugging Face 官方 datasets 流式迭代器进行固定种子的缓冲区抽样。"""
        try:
            import datasets
            from datasets import load_dataset
        except ImportError as exc:
            raise SourceError("配置要求 Hugging Face datasets 采集器，但当前环境未安装该可选组件。") from exc
        count = int(source.get("sample_count", 5000))
        seed = int(source.get("seed", 20260924))
        config_name = str(source.get("config", "default"))
        split = str(source.get("split", "train"))
        expected_fields = source.get("expected_fields", {"data": "list", "system_prompt": "str"})
        buffer_size = int(source.get("shuffle_buffer_size", max(10_000, count * 2)))
        if count < 1 or buffer_size < count:
            raise SourceError("sample_count 必须为正数，shuffle_buffer_size 不得小于抽样数量。")
        if verification["current_revision"] != str(source["revision"]):
            raise SourceError("数据集 revision 与配置不一致；停止采集。")
        try:
            dataset = load_dataset(
                str(source["dataset_id"]), name=config_name, split=split, revision=str(source["revision"]),
                streaming=True,
            )
            shuffled = dataset.shuffle(seed=seed, buffer_size=buffer_size)
            selected = [dict(row) for row in shuffled.take(count)]
        except Exception as exc:
            raise SourceError(f"Hugging Face datasets 流式读取失败（{type(exc).__name__}）。") from None
        if len(selected) != count:
            raise SourceError(f"数据集仅返回 {len(selected)}/{count} 条样本；不生成不完整样本文件。")
        field_types: dict[str, set[str]] = {}
        for row in selected:
            for name, value in row.items():
                field_types.setdefault(str(name), set()).add(type(value).__name__)
        for name, expected in expected_fields.items():
            observed = field_types.get(str(name), set())
            type_ok = (expected == "list" and all(kind in {"list", "tuple"} for kind in observed)) or (
                expected == "str" and all(kind == "str" for kind in observed)
            )
            if not observed or not type_ok:
                raise SourceError(f"字段结构与配置不符：{name} expected={expected}, observed={sorted(observed)}")
        collected_at = datetime.now(timezone.utc).isoformat()
        for position, row in enumerate(selected):
            row["hf_stream_position"] = position
            row["hf_row_idx"] = position
            row["collected_at"] = collected_at
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            raise SourceError(f"原始输出已存在，为保护原始数据未覆盖：{output_path}")
        temporary = output_path.with_suffix(output_path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            for row in selected:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        temporary.replace(output_path)
        report = {
            **verification, "revision": verification["current_revision"], "config": config_name, "split": split,
            "sample_count": len(selected), "sample_ids": [f"hf-stream:{index}" for index in range(len(selected))],
            "seed": seed, "sampling_method": "datasets IterableDataset.shuffle(seed, buffer_size).take(count); buffered deterministic sample, not a full-population uniform draw",
            "shuffle_buffer_size": buffer_size, "source_row_identifier": "stream_position; source dataset exposes no stable row ID in this reader",
            "field_types": {name: sorted(values) for name, values in sorted(field_types.items())},
            "collector": "huggingface/datasets", "collector_version": str(getattr(datasets, "__version__", "unknown")),
            "file": str(output_path.resolve()), "file_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
            "collected_at": collected_at, "license_boundary": "CC BY-NC data; local non-commercial research only unless additional permission is obtained.",
            "redistribution_authorized": False,
        }
        report_path = output_path.with_name("educhat_manifest.json")
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report

    @staticmethod
    def _validate_page_total(page: dict[str, Any], expected_rows: int) -> None:
        total = int(page.get("num_rows_total", 0))
        if expected_rows and total != expected_rows:
            raise SourceError(f"官方行接口返回的 split 大小与配置不一致（expected={expected_rows}, current={total}）。")
        if page.get("partial"):
            raise SourceError("官方行接口标记结果为 partial；为避免不完整采样，停止处理。")

    def _get_page(self, api_base: str, dataset_id: str, config: str, split: str, offset: int, length: int,
                  revision: str) -> dict[str, Any]:
        query = urlencode({"dataset": dataset_id, "config": config, "split": split, "revision": revision,
                           "offset": offset, "length": length})
        key = hashlib.sha256(f"{revision}|{query}".encode("utf-8")).hexdigest()
        return self._get_json(f"{api_base}?{query}", cache_key=f"rows_{key}")

    @staticmethod
    def _collect_rows(page: dict[str, Any], sample_rows: dict[int, dict[str, Any]], truncated_rows: set[int]) -> None:
        rows = page.get("rows")
        if not isinstance(rows, list):
            raise SourceError("官方行接口未返回 rows 数组。")
        for item in rows:
            if not isinstance(item, dict) or not isinstance(item.get("row"), dict):
                continue
            try:
                row_index = int(item.get("row_idx"))
            except (TypeError, ValueError):
                continue
            if item.get("truncated_cells"):
                truncated_rows.add(row_index)
                continue
            row = dict(item["row"])
            row["hf_row_idx"] = row_index
            sample_rows[row_index] = row
            truncated_rows.discard(row_index)
