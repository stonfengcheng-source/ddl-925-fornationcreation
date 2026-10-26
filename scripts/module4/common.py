from __future__ import annotations

import hashlib
import json
import math
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

TRAIN_VARIANTS = ("raw", "rule", "llm_only", "datajuicer", "ours")
EVAL_MODELS = ("base", *TRAIN_VARIANTS)
DISPLAY_NAMES = {
    "base": "Base",
    "raw": "Raw",
    "rule": "Rule",
    "llm_only": "LLM-only",
    "datajuicer": "Data-Juicer",
    "ours": "Ours",
}


def training_schedule(sample_count: int, batch_size: int, grad_acc: int, epochs: float, warmup_ratio: float = 0.1) -> dict:
    """为单进程训练预留至少一个非零学习率更新步。"""
    if min(sample_count, batch_size, grad_acc) < 1 or epochs <= 0 or not 0 <= warmup_ratio <= 1:
        raise ValueError("样本数、批量、梯度累积和轮数必须为正，预热比例必须在 0 到 1 之间")
    updates_per_epoch = math.ceil(sample_count / (batch_size * grad_acc))
    total_steps = max(1, math.ceil(updates_per_epoch * epochs))
    warmup_steps = min(math.ceil(total_steps * warmup_ratio), total_steps - 1)
    return {"estimated_optimizer_steps": total_steps, "warmup_steps": warmup_steps}

def read_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    path = Path(path)
    rows = []
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    with path.open("r", encoding="utf-8-sig") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{i} JSON 解析失败: {e}") from e
    return rows

def write_jsonl(path: str | Path, rows: Iterable[Dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

def get_text(row: Dict[str, Any], candidates: Sequence[str]) -> str:
    for key in candidates:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


class _EducationTextParser(HTMLParser):
    """将教育文本的 HTML 段落还原为换行，保留题目中的文本和实体。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"p", "div", "br", "li"}:
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def education_qa(row: Dict[str, Any]) -> tuple[str, str]:
    """兼容 Schema v1 中以“题目 / 答案 / 解析”组织的教育文本。"""
    text = get_text(row, ["raw_text", "clean_text", "masked_text"])
    if re.search(r"</?(?:p|div|br|span|li)\b", text, re.IGNORECASE):
        parser = _EducationTextParser()
        parser.feed(text)
        parser.close()
        text = "".join(parser.parts)
    match = re.fullmatch(
        r"\s*题目\s*[:：]\s*(?P<question>.*?)\n\s*答案\s*[:：][^\S\r\n]*"
        r"(?P<answer>.*?)(?:\n\s*解析\s*[:：]\s*(?P<analysis>.*?))?\s*",
        text, re.DOTALL,
    )
    if not match:
        return "", ""
    question, answer = match.group("question").strip(), match.group("answer").strip()
    if not question or not answer:
        return "", ""
    analysis = (match.group("analysis") or "").strip()
    return question, answer + (f"\n解析：{analysis}" if analysis else "")


def normalize_for_training(row: Dict[str, Any]) -> Dict[str, Any]:
    """统一为 LLaMA-Factory 的 Alpaca 监督微调格式。

    如果原记录同时包含 instruction 和 input，input 会被保留为上下文；只有在
    没有 instruction/question/prompt/query 时，才把 input 当作主问题使用。
    """
    instruction = get_text(row, ["instruction", "question", "prompt", "query"])
    input_text = get_text(row, ["input", "context"])
    if not instruction:
        instruction, input_text = input_text, ""
    output = get_text(row, ["output", "answer", "response", "target"])
    if not instruction or not output:
        question, answer = education_qa(row)
        instruction = instruction or question
        output = output or answer
    sample_id = str(row.get("id") or row.get("sample_id") or row.get("uuid") or "").strip()
    if not sample_id:
        raise ValueError("样本缺少统一 ID；请先由任务一分配 id")
    if not instruction or not output:
        raise ValueError(f"样本缺少问题/答案字段: id={sample_id}")
    normalized = {
        "id": sample_id,
        "instruction": instruction,
        "input": input_text,
        "output": output,
        "system": get_text(row, ["system", "system_prompt"]),
    }
    return normalized


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {
        "1", "true", "yes", "y", "pass", "passed", "keep", "clean", "通过"
    }


def content_digest(row: Dict[str, Any]) -> str:
    normalized = normalize_for_training(row)
    text = "\u241f".join(
        " ".join(normalized.get(key, "").split()).casefold()
        for key in ("instruction", "input", "output")
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sample_label(count: int) -> str:
    if count > 0 and count % 1000 == 0:
        return f"{count // 1000}k"
    return str(count)


def dataset_variants(data_dir: str | Path, count: int) -> tuple[list[str], dict[str, str]]:
    """按数据清单选择已有组；留空的上游组不读取历史遗留文件。"""
    path = Path(data_dir) / f"dataset_manifest_{sample_label(count)}.json"
    if not path.is_file():
        return list(TRAIN_VARIANTS), {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    active = [name for name in TRAIN_VARIANTS if name in manifest.get("variants", {})]
    if not active:
        raise ValueError(f"数据清单没有可验证的数据组：{path}")
    return active, manifest.get("pending_variants", {})


def ensure_unique_ids(rows: Iterable[Dict[str, Any]], source_name: str) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    output: List[Dict[str, Any]] = []
    for index, row in enumerate(rows, 1):
        sample_id = str(row.get("id") or row.get("sample_id") or row.get("uuid") or "").strip()
        if not sample_id:
            raise ValueError(f"{source_name} 第 {index} 条缺少统一 ID")
        if sample_id in seen:
            raise ValueError(f"{source_name} 存在重复 ID: {sample_id}")
        seen.add(sample_id)
        output.append({**row, "id": sample_id})
    return output


def deduplicate_content(rows: Iterable[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], int]:
    seen: set[str] = set()
    output: List[Dict[str, Any]] = []
    duplicate_count = 0
    for row in rows:
        digest = content_digest(row)
        if digest in seen:
            duplicate_count += 1
            continue
        seen.add(digest)
        output.append(row)
    return output, duplicate_count
