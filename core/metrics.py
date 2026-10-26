from __future__ import annotations
import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from . import config

def p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return float(ordered[index])

def _stats(rows: list[dict]) -> dict:
    total = len(rows)
    passed = sum(1 for row in rows if row["status"] == "passed")
    latencies = [row["latency"] for row in rows if row.get("latency") is not None]
    tokens = [row["tokens"] for row in rows if row.get("tokens")]
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "avg_latency_s": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
        "p95_latency_s": round(p95(latencies), 3),
        "avg_tokens": round(sum(tokens) / len(tokens), 1) if tokens else 0.0,
    }

def _gate(name: str, value: float, threshold: float, reverse: bool = False) -> dict:
    passed = value <= threshold if reverse else value >= threshold
    return {"name": name, "value": round(float(value), 4),
            "threshold": float(threshold), "passed": passed}


@dataclass
class RunContext:
    run_id: str
    started_at: str
    mode: str
    model: str
    cases: list = field(default_factory=list)
    extraction: dict | None = None

    @classmethod
    def new(cls) -> "RunContext":
        now = datetime.now()
        return cls(
            run_id=now.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4],
            started_at=now.isoformat(timespec="seconds"),
            mode="fake" if config.USE_FAKE else "real",
            model="fake-oracle" if config.USE_FAKE else config.MODEL_NAME,
        )

    def add_case(self, case_id: str, category: str, status: str,
                 latency: float, tokens: int, detail: str = "") -> None:
        self.cases.append({
            "id": case_id,
            "category": category,
            "status": status,
            "latency": round(float(latency or 0), 3),
            "tokens": int(tokens or 0),
            "detail": detail,
        })

    def set_extraction(self, report: dict) -> None:
        self.extraction = report

    def category_stats(self) -> dict:
        groups: dict[str, list[dict]] = {}
        for row in self.cases:
            groups.setdefault(row["category"], []).append(row)
        return {name: _stats(rows) for name, rows in groups.items()}

    def gates(self) -> list[dict]:
        gates: list[dict] = []
        if self.extraction:
            gates.append(_gate(
                "json_valid_rate",
                self.extraction.get("json_valid_rate", 0.0),
                config.THRESHOLDS["json_valid_rate"],
            ))
            gates.append(_gate(
                "field_accuracy",
                self.extraction.get("field_accuracy", 0.0),
                config.THRESHOLDS["field_accuracy"],
            ))
        if self.cases:
            gates.append(_gate(
                "p95_latency_s",
                p95([row["latency"] for row in self.cases]),
                config.THRESHOLDS["p95_latency_s"],
                reverse=True,
            ))
        return gates

    def summary(self) -> dict:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "mode": self.mode,
            "model": self.model,
            "total": _stats(self.cases),#调用stats算整体情况
            "categories": self.category_stats(),#算每一类的情况
            "extraction": self.extraction or {},
            "gates": self.gates(),
            "cases": self.cases,
        }


def format_lines(summary: dict) -> list[str]:
    lines = [f"运行 {summary['run_id']}｜模式 {summary['mode']}｜模型 {summary['model']}"]
    for gate in summary.get("gates", []):
        flag = "PASS" if gate["passed"] else "FAIL"
        lines.append(f"  [{flag}] {gate['name']} = {gate['value']}（阈值 {gate['threshold']}）")
    for name, stats in summary.get("categories", {}).items():
        lines.append(
            f"  {name}: {stats['passed']}/{stats['total']} 通过"
            f"，P95 {stats['p95_latency_s']}s，平均 token {stats['avg_tokens']}"
        )
    return lines


def write_artifacts(summary: dict, base_dir: Path | None = None) -> Path:
    base = Path(base_dir or config.ARTIFACT_DIR)
    out_dir = base / summary["run_id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    text = json.dumps(summary, ensure_ascii=False, indent=2)

    (out_dir / "metrics.json").write_text(text, encoding="utf-8")
    latest = base / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    (latest / "metrics.json").write_text(text, encoding="utf-8")
    return out_dir
