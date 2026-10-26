"""网页与命令行共用的评测科目、档位和选择校验。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

OPTIONS_PATH = Path(__file__).resolve().parents[2] / "configs/module4/evaluation_options.json"
EVALUATION_OPTIONS = json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))
EVAL_PROFILES = {profile["value"]: profile for profile in EVALUATION_OPTIONS["profiles"]}
SUBJECT_IDS = {subject["value"] for subject in EVALUATION_OPTIONS["subjects"]}


def resolve_selection(mode: str, subjects=None, sample_limit=None, all_questions=False):
    if mode not in {*EVAL_PROFILES, "custom"}:
        raise ValueError("请选择有效的评测模式")
    if mode != "custom":
        profile = EVAL_PROFILES[mode]
        return sorted(profile["subjects"]), profile["samples_per_subject"]
    if not isinstance(subjects, list) or not subjects:
        raise ValueError("请至少选择一个评测科目")
    if any(not isinstance(subject, str) or subject not in SUBJECT_IDS for subject in subjects):
        raise ValueError("评测科目包含不支持的科目")
    if not isinstance(all_questions, bool):
        raise ValueError("全部题目选项必须是布尔值")
    if all_questions:
        limit = None
    else:
        if isinstance(sample_limit, bool) or not isinstance(sample_limit, int) or not 1 <= sample_limit <= 10000:
            raise ValueError("每科题量必须是 1 到 10000 之间的整数")
        limit = sample_limit
    return sorted(set(subjects)), limit


def selection_fingerprint(subjects, sample_limit):
    payload = json.dumps([sorted(subjects), sample_limit], separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:12]
