"""命令行入口：python -m data_pipeline run --config configs/preproject_pipeline.json"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .pipeline import _read_local_source, run_pipeline, sha256_file
from .schema import _stable_sample_id
from .source import DatasetViewerClient
from .viewer_import import import_viewer_pages

def _load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"配置文件无法读取：{config_path}（{type(exc).__name__}）") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"配置 JSON 无效：第 {exc.lineno} 行，第 {exc.colno} 列。") from None
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise ValueError("配置顶层必须是对象，且 schema_version 必须为 1。")
    return config

def _absolute(value: str | Path, root: Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="预立项教育文本数据处理闭环")
    commands = parser.add_subparsers(dest="command", required=True)
    run_parser = commands.add_parser("run", help="采集（如缺少原始文件）并执行完整处理闭环")
    run_parser.add_argument("--config", default="configs/preproject_pipeline.json")
    run_parser.add_argument("--input", help="本地 JSONL 输入；提供后跳过在线采集")
    run_parser.add_argument("--source-manifest", help="本地来源清单；若存在则校验输入文件 SHA-256")
    run_parser.add_argument("--out-dir", help="覆盖配置中的输出目录")
    run_parser.add_argument("--data-subset-id", help="为本次实际样本规模指定独立数据子集版本标识")
    fetch_parser = commands.add_parser("fetch", help="只采集固定 revision 的官方公开样本")
    fetch_parser.add_argument("--config", default="configs/preproject_pipeline.json")
    fetch_parser.add_argument("--out", help="覆盖配置中的原始 JSONL 路径")
    fetch_parser.add_argument("--count", type=int, choices=(200, 5000), help="固定样本数；200 用于试运行，5000 用于主实验")
    manifest_parser = commands.add_parser("manifest", help="为用户提供的 JSONL/JSON/Parquet 生成可追溯来源清单")
    manifest_parser.add_argument("--config", default="configs/preproject_pipeline.json")
    manifest_parser.add_argument("--input", required=True)
    manifest_parser.add_argument("--dataset-id", required=True)
    manifest_parser.add_argument("--source-url", required=True)
    manifest_parser.add_argument("--license", required=True)
    manifest_parser.add_argument("--revision", required=True)
    manifest_parser.add_argument("--split", default="local")
    manifest_parser.add_argument("--out", help="清单输出路径，默认与输入文件同目录 educhat_manifest.json")
    viewer_parser = commands.add_parser("import-viewer-pages", help="核验并合并本地 Hugging Face Dataset Viewer /rows 响应")
    viewer_parser.add_argument("--config", default="configs/preproject_pipeline.json")
    viewer_parser.add_argument("--page", action="append", nargs=3, metavar=("OFFSET", "LENGTH", "JSON_FILE"),
                               required=True, help="可重复指定，例：--page 0 100 data/educhat_page_0.json")
    viewer_parser.add_argument("--out", default="data/preproject/incoming/200/educhat_raw_200.jsonl",
                               help="输出 JSONL；已有文件不会覆盖")
    args = parser.parse_args(argv)
    try:
        root = Path.cwd()
        config_path = _absolute(args.config, root)
        config = _load_config(config_path)
        source = dict(config.get("source", {}))
        if args.command == "import-viewer-pages":
            page_inputs = [(int(offset), int(length), _absolute(path, root))
                           for offset, length, path in args.page]
            output_path = _absolute(args.out, root)
            result = import_viewer_pages(page_inputs, output_path=output_path, config=config)
            print(json.dumps({"output": str(output_path.resolve()), **result}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "manifest":
            raw_path = _absolute(args.input, root)
            if not raw_path.is_file():
                raise FileNotFoundError(f"输入文件不存在：{raw_path}")
            rows, issues, _nonblank, _errors = _read_local_source(raw_path)
            dataset_id = args.dataset_id.strip()
            revision = args.revision.strip()
            split = args.split.strip()
            if not dataset_id or not revision or not split:
                raise ValueError("dataset-id、revision 和 split 不能为空；未知 revision 请明确填写 unversioned。")
            source_ids = [str(row.get("id", row.get("hf_row_idx", row.get("row_idx", line)))) for line, row in rows]
            sample_ids = [str(row.get("sample_id") or _stable_sample_id(dataset_id, revision, split, source_id))
                          for (line, row), source_id in zip(rows, source_ids)]
            fields = sorted({str(key) for _line, row in rows for key in row})
            field_types: dict[str, list[str]] = {}
            for field in fields:
                field_types[field] = sorted({type(row.get(field)).__name__ for _line, row in rows if field in row})
            output = _absolute(args.out, root) if args.out else raw_path.with_name("educhat_manifest.json")
            manifest = {
                "manifest_version": 1,
                "dataset_id": dataset_id,
                "source_url": args.source_url.strip(),
                "license": args.license.strip(),
                "revision": revision,
                "split": split,
                "sampling_method": "user_provided_local_file; no sampling performed by manifest command",
                "sample_count": len(rows),
                "sample_ids": sample_ids,
                "source_record_ids": source_ids,
                "field_names": fields,
                "field_types": field_types,
                "parse_issue_count": len(issues),
                "file": raw_path.name,
                "file_sha256": sha256_file(raw_path),
                "acquired_at": datetime.now(timezone.utc).isoformat(),
                "provenance_method": "user_attested_local_import",
                "revision_verified": False,
                "license_verified": False,
                "official_revision_verified": False,
                "redistribution_authorized": False,
            }
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"manifest": str(output.resolve()), "sample_count": len(rows),
                              "file_sha256": manifest["file_sha256"], "parse_issue_count": len(issues)},
                             ensure_ascii=False, indent=2))
            return 0
        if args.command == "fetch":
            if not source.get("enabled"):
                raise ValueError("配置中的 source.enabled 未启用。")
            if args.count:
                source["sample_count"] = args.count
            default_output = ("data/preproject/raw/educhat_raw_200.jsonl" if args.count == 200 else
                              source.get("raw_output", "data/preproject/raw/educhat_raw_5k.jsonl"))
            target = _absolute(args.out or default_output, root)
            if target.exists():
                raise FileExistsError(f"原始文件已存在，为保护原始数据未覆盖：{target}")
            cache = _absolute(source.get("cache_dir", "data/preproject/cache"), root)
            result = DatasetViewerClient(source, cache).sample(source, target)
            keys = ("sample_count", "current_revision", "license", "file_sha256", "file")
            print(json.dumps({key: result[key] for key in keys}, ensure_ascii=False, indent=2))
            return 0
        target_dir = _absolute(args.out_dir or config.get("output_dir", "data/preproject/processed"), root)
        if args.data_subset_id:
            subset_id = args.data_subset_id.strip()
            if not subset_id:
                raise ValueError("data-subset-id 不能为空。")
            config["data_subset_id"] = subset_id
        input_path = _absolute(args.input, root) if args.input else None
        if input_path is None and source.get("enabled"):
            raw_path = _absolute(source.get("raw_output", "data/preproject/raw/educhat_raw_5k.jsonl"), root)
            if raw_path.exists():
                input_path = raw_path
                manifest_path = raw_path.with_name("educhat_manifest.json")
                if not manifest_path.is_file():
                    manifest_path = raw_path.with_name("source_manifest.json")
                if manifest_path.is_file():
                    try:
                        source["_verified_manifest"] = json.loads(manifest_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        pass
                config["source"] = source
        manifest_path = _absolute(args.source_manifest, root) if args.source_manifest else None
        result = run_pipeline(input_path=input_path, output_dir=target_dir, config=config,
                              config_path=config_path, source_manifest_path=manifest_path)
        print(json.dumps({"output_dir": result["output_dir"], "statistics": result["statistics"], "quality_gate": result["gate"]},
                         ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"数据处理未完成：{exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
