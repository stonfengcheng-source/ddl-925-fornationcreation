"""精确、归一化与近似重复检测；近似重复只进入人工复核。"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from typing import Any


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, value: str) -> str:
        self.parent.setdefault(value, value)
        if self.parent[value] != value:
            self.parent[value] = self.find(self.parent[value])
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def _text(record: dict[str, Any]) -> str:
    return "\x1f".join(str(record.get(key, "")) for key in ("instruction", "input", "output"))


def _normalized(record: dict[str, Any]) -> str | None:
    value = unicodedata.normalize("NFKC", _text(record)).casefold()
    fields = [re.sub(r"[^\w]+", "", field, flags=re.UNICODE) for field in value.split("\x1f")]
    if not fields[0] or not fields[2]:
        return None
    return "\x1f".join(fields)


def _simhash(text: str) -> int:
    text = unicodedata.normalize("NFKC", text).casefold()
    tokens: list[str] = []
    for field in text.split("\x1f"):
        compact = "".join(field.split())
        if not compact:
            continue
        if len(compact) <= 3:
            tokens.append(compact)
        else:
            tokens.extend(compact[index:index + 3] for index in range(len(compact) - 2))
    if not tokens:
        return 0
    weights = [0] * 64
    for token in tokens:
        bitstring = int.from_bytes(hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(), "big")
        for bit in range(64):
            weights[bit] += 1 if bitstring & (1 << bit) else -1
    return sum((1 << bit) for bit, weight in enumerate(weights) if weight >= 0)


def _bands(value: int) -> tuple[int, int, int, int]:
    return tuple((value >> (16 * band)) & 0xFFFF for band in range(4))  # type: ignore[return-value]


def _hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def deduplicate(records: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    seen_ids: dict[str, dict[str, Any]] = {}
    records_by_id: dict[str, dict[str, Any]] = {}
    id_conflicts: set[str] = set()
    for record in records:
        sample_id = str(record.get("sample_id", ""))
        records_by_id[sample_id] = record
        previous = seen_ids.get(sample_id)
        if previous and previous.get("raw_record_sha256") != record.get("raw_record_sha256"):
            id_conflicts.add(sample_id)
        else:
            seen_ids[sample_id] = record
    for record in records:
        if record.get("sample_id") in id_conflicts:
            record["processing_status"] = "quarantine"
            record["processing_reasons"].append("sample_id_version_conflict")

    uf = _UnionFind()
    exact_seen: dict[str, dict[str, Any]] = {}
    normalized_seen: dict[str, dict[str, Any]] = {}
    exact_duplicates = 0
    normalized_duplicates = 0
    near_edges: list[tuple[str, str, int]] = []
    buckets: dict[tuple[int, int], list[tuple[str, int]]] = defaultdict(list)
    fingerprints: dict[str, int] = {}
    distance_limit = int(config.get("near_duplicate_hamming_distance", 3))
    min_near_chars = int(config.get("near_duplicate_min_chars", 12))
    enabled = bool(config.get("near_duplicate_enabled", True))

    for record in records:
        sample_id = str(record["sample_id"])
        exact_key = _text(record)
        prior = exact_seen.get(exact_key)
        if prior is not None:
            exact_duplicates += 1
            if record["processing_status"] != "quarantine":
                record["processing_status"] = "drop"
            record["processing_reasons"].append("exact_duplicate")
            record["duplicate_of"] = prior["sample_id"]
            record["duplicate_type"] = "exact"
            record["deduplication_audit"] = {"type": "exact", "action": "drop", "representative_sample_id": prior["sample_id"]}
            uf.union(sample_id, str(prior["sample_id"]))
            continue
        exact_seen[exact_key] = record

        normalized_key = _normalized(record)
        prior = normalized_seen.get(normalized_key) if normalized_key is not None else None
        if prior is not None:
            normalized_duplicates += 1
            if record["processing_status"] != "quarantine":
                record["processing_status"] = "drop"
            record["processing_reasons"].append("normalized_duplicate")
            record["duplicate_of"] = prior["sample_id"]
            record["duplicate_type"] = "normalized"
            record["deduplication_audit"] = {"type": "normalized", "action": "drop", "representative_sample_id": prior["sample_id"]}
            uf.union(sample_id, str(prior["sample_id"]))
            continue
        if normalized_key is not None:
            normalized_seen[normalized_key] = record

        if record.get("processing_status") in {"drop", "quarantine"}:
            continue
        fingerprint = _simhash(exact_key)
        if enabled and len("".join(str(record.get(key, "")) for key in ("instruction", "input", "output"))) >= min_near_chars:
            candidates: set[str] = set()
            if distance_limit > 3:
                # Four 16-bit bands guarantee a shared band only at distance <= 3.
                candidates.update(fingerprints)
            else:
                for band, value in enumerate(_bands(fingerprint)):
                    candidates.update(sample for sample, _ in buckets[(band, value)])
            for previous_id in sorted(candidates):
                previous_hash = fingerprints[previous_id]
                distance = _hamming(fingerprint, previous_hash)
                if distance <= distance_limit:
                    near_edges.append((previous_id, sample_id, distance))
                    uf.union(previous_id, sample_id)
                    previous = records_by_id.get(previous_id)
                    if previous and previous["processing_status"] in {"keep", "repair"}:
                        previous["processing_status"] = "review"
                        previous["processing_reasons"].append("near_duplicate_requires_review")
                        previous["duplicate_type"] = "near_approximate"
                        previous["deduplication_audit"] = {"type": "near_approximate", "action": "review", "representative_sample_id": previous_id}
                    if previous_id not in record["near_duplicate_sample_ids"]:
                        record["near_duplicate_sample_ids"].append(previous_id)
                    if sample_id not in previous["near_duplicate_sample_ids"]:
                        previous["near_duplicate_sample_ids"].append(sample_id)
                    if record["processing_status"] in {"keep", "repair"}:
                        record["processing_status"] = "review"
                        record["processing_reasons"].append("near_duplicate_requires_review")
                        record["duplicate_type"] = "near_approximate"
                        record["deduplication_audit"] = {"type": "near_approximate", "action": "review", "representative_sample_id": min(previous_id, sample_id)}
            for band, value in enumerate(_bands(fingerprint)):
                buckets[(band, value)].append((sample_id, fingerprint))
            fingerprints[sample_id] = fingerprint

    clusters: dict[str, list[str]] = defaultdict(list)
    for sample_id in uf.parent:
        clusters[uf.find(sample_id)].append(sample_id)
    cluster_list = [sorted(values) for values in clusters.values() if len(values) > 1]
    cluster_list.sort(key=lambda values: values[0])
    for cluster in cluster_list:
        representative = cluster[0]
        for sample_id in cluster:
            record = records_by_id.get(sample_id)
            if record is None:
                continue
            record["duplicate_cluster_id"] = representative
            record["duplicate_representative_sample_id"] = representative
    near_ids = {sample_id for left, right, _ in near_edges for sample_id in (left, right)}
    question_answers: dict[str, set[str]] = defaultdict(set)
    question_samples: dict[str, list[str]] = defaultdict(list)
    for record in records:
        if record.get("processing_status") in {"drop", "quarantine"}:
            continue
        question = unicodedata.normalize("NFKC", str(record.get("instruction", ""))).casefold()
        question = re.sub(r"[^\w]+", "", question, flags=re.UNICODE)
        answer = unicodedata.normalize("NFKC", str(record.get("output", ""))).casefold()
        answer = re.sub(r"\s+", " ", answer).strip()
        if question:
            question_answers[question].add(answer)
            question_samples[question].append(str(record["sample_id"]))
    answer_conflicts = [
        {"sample_ids": sorted(question_samples[key]), "answer_variant_count": len(answers)}
        for key, answers in question_answers.items() if len(answers) > 1
    ]
    for conflict in answer_conflicts:
        for sample_id in conflict["sample_ids"]:
            record = records_by_id.get(sample_id)
            if record and record["processing_status"] in {"keep", "repair"}:
                record["processing_status"] = "review"
                record["processing_reasons"].append("answer_conflict_requires_review")
    repeated_question_group_count = sum(1 for samples in question_samples.values() if len(samples) > 1)

    return {
        "input_count": len(records),
        "exact_duplicate_count": exact_duplicates,
        "normalized_duplicate_count": normalized_duplicates,
        "near_duplicate_sample_count": len(near_ids),
        "near_duplicate_pair_count": len(near_edges),
        "near_duplicate_pairs": [
            {"sample_ids": [left, right], "hamming_distance": distance}
            for left, right, distance in near_edges
        ],
        "duplicate_clusters": cluster_list,
        "answer_conflict_count": len(answer_conflicts),
        "repeated_question_group_count": repeated_question_group_count,
        "answer_conflicts": answer_conflicts,
        "sample_id_conflict_count": len(id_conflicts),
        "sample_id_conflicts": sorted(id_conflicts),
        "retained_after_exact_normalized": len(records) - exact_duplicates - normalized_duplicates,
        "near_duplicate_policy": "flag_for_review; never_auto_drop",
        "parameters": {"near_duplicate_enabled": enabled, "hamming_distance_threshold": distance_limit,
                       "near_duplicate_min_chars": min_near_chars, "normalization": "NFKC+casefold+nonword_removal"},
        "engine": "native-simhash-v1",
    }
