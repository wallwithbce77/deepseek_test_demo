from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from . import config

FILES = {
    "functional": "cases_functional.json",
    "instruction": "cases_instruction.json",
    "grounding": "cases_grounding.json",
    "safety": "cases_safety.json",
    "boundary": "cases_boundary.json",
    "extraction": "extract_samples.json",
}
CHAT_KINDS = tuple(kind for kind in FILES if kind != "extraction")

def load(kind: str) -> list[dict]:
    if kind not in FILES:
        raise ValueError(f"unknown kind {kind}")
    path = config.DATA_DIR / FILES[kind]
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise TypeError(f"{path.name}顶层必须是json")
    return data

def chat_cases() -> list[dict]:
    cases: list[dict] = []
    for kind in CHAT_KINDS:
        cases.extend(load(kind))
    return cases

def load_all() -> dict[str, dict]:
    cases: dict[str, dict] = {}
    for kind in FILES:
        for case in load(kind):
            case_id = case.get("id")
            if not case_id:
                raise ValueError(f"{FILES[kind]} 中存在缺少 id 的用例")
            if case_id in cases:
                raise ValueError(f"用例 id 重复：{case_id}")
            cases[case_id] = {"kind": kind, "case": case}
    return cases

def data_path(kind: str) -> Path:
    return config.DATA_DIR / FILES[kind]