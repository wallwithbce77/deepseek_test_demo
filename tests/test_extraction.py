from __future__ import annotations
import json
import pytest
from core import config, dataset
from core.metrics import p95
from core.validators import score_fields, strip_fence

SAMPLES = dataset.load("extraction")


FIELD_DESCRIPTIONS = {
    "order_no": "订单编号",
    "supplier": "供应商名称",
    "amount": "订单金额",
    "deliver_date": "交付日期",
    "item_count": "明细项数量，即物料明细行数，不是数量列的合计",
    "total_amount": "全部明细金额合计，即各行数量乘以单价后求和",
}


def _type_cn(value) -> str:
    if value is None:
        return "字符串或 null"
    if isinstance(value, bool):
        return "布尔值"
    if isinstance(value, (int, float)):
        return "数字"
    if isinstance(value, list):
        return "数组"
    if isinstance(value, dict):
        return "对象"
    return "字符串"


def build_prompt(sample: dict) -> str:
    fields = "\n".join(
        f"- {name}：{FIELD_DESCRIPTIONS.get(name, name)}；"
        f"类型为{_type_cn(value)}"
        for name, value in sample["expected"].items()
    )

    return (
        "你是企业采购单据的信息抽取器。"
        "请从下面的文本中抽取指定字段，输出一个 JSON 对象。\n"
        "字段定义：\n"
        f"{fields}\n"
        "要求：\n"
        "1. 只输出 JSON，不要 Markdown 代码块，不要解释。\n"
        "2. 文本中不存在的字段输出 null。\n"
        "3. 数字不带千分位和货币符号。\n"
        "4. 日期统一为 YYYY-MM-DD。\n"
        "5. item_count 只统计物料明细行数，"
        "不要对数量列求和。\n"
        f"文本：\n{sample['text']}"
    )

@pytest.fixture(scope="session")
def extraction_report(api_client, run_ctx):
    rows = []
    for sample in SAMPLES:
        result = api_client.ask(build_prompt(sample), case_id=sample["id"],
                                response_format={"type": "json_object"}, max_tokens=2048)
        parsed, parse_error = None, ""
        try:
            parsed = json.loads(strip_fence(result.content))
        except ValueError as exc:
            parse_error = str(exc)[:120]
        scored = score_fields(parsed, sample["expected"])
        rows.append({
            "id": sample["id"], "status_code": result.status_code, "json_ok": parsed is not None,
            "parse_error": parse_error, "latency": result.elapsed, "tokens": result.total_tokens,
            "correct": scored["correct"], "total": scored["total"], "fields": scored["fields"],
        })

    total_fields = sum(row["total"] for row in rows)
    correct_fields = sum(row["correct"] for row in rows)
    field_stats: dict[str, dict] = {}
    for row in rows:
        for name, item in row["fields"].items():
            bucket = field_stats.setdefault(name, {"total": 0, "correct": 0})
            bucket["total"] += 1
            bucket["correct"] += 1 if item["ok"] else 0

    report = {
        "samples": len(rows),
        "status_ok_rate": round(sum(r["status_code"] == 200 for r in rows) / len(rows), 4),
        "json_valid_rate": round(sum(r["json_ok"] for r in rows) / len(rows), 4),
        "field_accuracy": round(correct_fields / total_fields, 4) if total_fields else 0.0,
        "exact_match_rate": round(sum(r["correct"] == r["total"] for r in rows) / len(rows), 4),
        "p95_latency_s": round(p95([r["latency"] for r in rows]), 3),
        "fields": {name: {**stat, "accuracy": round(stat["correct"] / stat["total"], 4)}
                   for name, stat in sorted(field_stats.items())},
        "rows": rows,
    }
    run_ctx.set_extraction(report)
    return report


def test_all_samples_responded(extraction_report):
    failed = [r["id"] for r in extraction_report["rows"] if r["status_code"] != 200]
    assert extraction_report["status_ok_rate"] == 1.0, f"以下样本请求失败：{failed}"


def test_json_compliance_gate(extraction_report):
    rate, threshold = extraction_report["json_valid_rate"], config.THRESHOLDS["json_valid_rate"]
    bad = [r["id"] for r in extraction_report["rows"] if not r["json_ok"]]
    assert rate >= threshold, f"JSON 合规率 {rate:.2%} 低于 {threshold:.2%}；不合规：{bad}"


def test_field_accuracy_gate(extraction_report):
    accuracy, threshold = extraction_report["field_accuracy"], config.THRESHOLDS["field_accuracy"]
    per_field = {name: stat["accuracy"] for name, stat in extraction_report["fields"].items()}
    assert accuracy >= threshold, f"字段准确率 {accuracy:.2%} 低于 {threshold:.2%}；逐字段：{per_field}"
