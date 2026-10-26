"""在不改动权重的前提下保留 Transformers 4/5 都能读取的模型参数。"""
from __future__ import annotations

import copy
import argparse
import json
import os
import struct
import tempfile
from pathlib import Path


def legacy_compatible_config(config: dict) -> dict:
    result = copy.deepcopy(config)
    if result.get("dtype") is not None:
        if result.get("torch_dtype") not in {None, result["dtype"]}:
            raise ValueError("模型 dtype 与 torch_dtype 不一致，请检查导出配置")
        result["torch_dtype"] = result["dtype"]
    rope = result.get("rope_parameters")
    if isinstance(rope, dict) and "rope_theta" in rope:
        if result.get("rope_theta") not in {None, rope["rope_theta"]}:
            raise ValueError("模型两种格式的 rope_theta 不一致")
        result["rope_theta"] = rope["rope_theta"]
        if rope.get("rope_type", "default") != "default":
            scaling = {key: value for key, value in rope.items() if key != "rope_theta"}
            if result.get("rope_scaling") not in (None, scaling):
                raise ValueError("模型两种格式的 rope_scaling 不一致")
            result["rope_scaling"] = scaling
    if isinstance(result.get("text_config"), dict):
        result["text_config"] = legacy_compatible_config(result["text_config"])
    return result


def normalize_export_config(model_dir: Path) -> dict:
    path = Path(model_dir) / "config.json"
    original = json.loads(path.read_text(encoding="utf-8"))
    compatible = legacy_compatible_config(original)
    if compatible != original:
        # 原模型目录与评测目录可能通过硬链接共享文件，原子替换避免连带修改另一目录。
        descriptor, temporary = tempfile.mkstemp(prefix="config-", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(compatible, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return compatible


def lora_update_status(path: Path) -> dict:
    """直接读取 safetensors 中的 B 矩阵，检查是否仍为全零初始化。"""
    with Path(path).open("rb") as handle:
        size = struct.unpack("<Q", handle.read(8))[0]
        if size > 100_000_000:
            raise ValueError("适配器文件头异常")
        header = json.loads(handle.read(size))
        data_start = 8 + size
        matrices = [value for key, value in header.items() if "lora_B" in key]
        nonzero = 0
        for matrix in matrices:
            begin, end = matrix["data_offsets"]
            handle.seek(data_start + begin)
            if any(handle.read(end - begin)):
                nonzero += 1
    return {"lora_b_matrices": len(matrices), "nonzero_lora_b_matrices": nonzero, "has_update": nonzero > 0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--models", nargs="*", default=[])
    args = parser.parse_args()
    from transformers import AutoConfig

    base = AutoConfig.from_pretrained(args.base_model, trust_remote_code=True)
    for path in args.models:
        effective = AutoConfig.from_pretrained(path, trust_remote_code=True)
        for field in ("model_type", "hidden_size", "num_hidden_layers", "rope_theta", "rope_scaling"):
            if getattr(base, field, None) != getattr(effective, field, None):
                raise ValueError(f"{path} 的 {field} 与 Base 不一致，请重新生成评测配置")
        print(f"[兼容检查通过] {path}: rope_theta={getattr(effective, 'rope_theta', None)}, torch_dtype={effective.torch_dtype}")


if __name__ == "__main__":
    main()
