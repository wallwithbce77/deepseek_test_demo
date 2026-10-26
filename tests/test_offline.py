from __future__ import annotations
from collections import Counter
import pytest
from core import dataset
from core.metrics import p95
from core.validators import (
    RULE_MAP, check_contains_expected, check_json_fields, check_numbered_steps,
    check_refusal, normalize_text, normalize_value, score_fields, strip_fence,
    to_halfwidth, values_equal,
)

CHAT = dataset.chat_cases()
EXTRACTION = dataset.load("extraction")
CATEGORIES = {"正常功能", "指令遵循", "资料忠实度", "安全", "边界测试"}
FIELDS = {"order_no", "supplier", "amount", "deliver_date", "item_count", "total_amount"}

def test_ids_and_fields():
    ids = [c["id"] for c in CHAT] + [c["id"] for c in EXTRACTION]
    assert len(ids) == len(set(ids)), "存在重复 id"
    assert len(CHAT) == 30, f"对话用例应为 30 条，实际 {len(CHAT)}"
    for case in CHAT:
        assert case["category"] in CATEGORIES
        assert case["question"] is not None
        assert case["checks"]
        assert case["language"] in {"zh", "en", "de", "fr", "mixed"}
        assert case["difficulty"] in {"easy", "normal", "hard"}


def test_rules_and_expected_types():
    for case in CHAT:
        checks, expected = case["checks"], case.get("expected")
        for rule in checks:
            assert rule in RULE_MAP, f"[{case['id']}] 未注册规则 {rule}"
        if "contains_expected" in checks:
            assert isinstance(expected, (str, list)) and expected
        if "grounded_answer" in checks:
            assert isinstance(expected, str) and expected
        if "json_fields" in checks:
            assert isinstance(expected, dict) and expected
        if "length_at_most" in checks or "numbered_steps" in checks:
            assert isinstance(expected, int) and expected > 0
        if "refusal" in checks:
            assert isinstance(expected, dict) and expected.get("markers")
    assert [c["id"] for c in CHAT if c["checks"] == ["not_empty"]] == ["B001"]


def test_category_coverage():
    counter = Counter(c["category"] for c in CHAT)
    assert set(counter) == CATEGORIES, f"分类不完整：{sorted(counter)}"
    assert all(count == 6 for count in counter.values()), f"每类应为 6 条：{dict(counter)}"


def test_extraction_schema():
    assert len(EXTRACTION) >= 12
    for sample in EXTRACTION:
        assert sample["language"] in {"zh", "en", "de", "mixed"}
        assert sample["difficulty"] in {"easy", "normal", "hard"}
        assert sample["layout"] and sample["text"].strip() and sample["expected"]
        for field, value in sample["expected"].items():
            assert field in FIELDS, f"[{sample['id']}] 未登记字段 {field}"
            assert value is None or isinstance(value, (str, int, float))


def test_normalization():
    assert to_halfwidth("ＰＯ－２０２７") == "PO-2027"
    assert strip_fence('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert normalize_text("H₂O") == "H2O"


def test_dates():
    assert normalize_value("2026年12月1日") == "2026-12-01"
    assert normalize_value("2026/12/01") == "2026-12-01"
    assert normalize_value("15.03.2027") == "2027-03-15"


def test_amounts():
    assert normalize_value("￥12,800.00") == 12800.0
    assert normalize_value("8,450.50") == 8450.5
    assert normalize_value("1.234,56 €") == 1234.56
    assert normalize_value("EUR 9.876,54") == 9876.54


def test_digit_boundary_and_values():
    check_contains_expected("答案是 2", "2")
    with pytest.raises(AssertionError):
        check_contains_expected("12", "2")
    assert values_equal("12800.00", 12800) is True
    assert values_equal("资料不足。", "资料不足") is True


def test_json_fence_and_bool():
    check_json_fields('```json\n{"name": "张三", "age": 30}\n```',
                      {"name": "string", "age": "integer"})
    with pytest.raises(AssertionError):
        check_json_fields('{"age": true}', {"age": "integer"})


def test_numbered_steps():
    check_numbered_steps("以下是三个步骤：\n**1.** 切菜\n**2.** 炒菜\n**3.** 装盘", 3)
    with pytest.raises(AssertionError):
        check_numbered_steps("1. 切菜\n2. 炒菜", 3)


def test_refusal():
    check_refusal("抱歉，我不能提供这个信息。", {"markers": ["抱歉", "不能"], "forbidden": ["步骤"]})
    with pytest.raises(AssertionError):
        check_refusal("好的，步骤如下：先准备材料。", {"markers": ["抱歉", "不能"]})


def test_score_fields_and_p95():
    assert score_fields({"supplier": None}, {"supplier": None})["correct"] == 1
    assert score_fields(None, {"supplier": None})["correct"] == 0
    assert p95([1, 2, 3, 4, 5]) == 5.0
