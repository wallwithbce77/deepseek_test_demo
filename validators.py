import json
import re

def check_not_empty(answer, expected=None):
    assert len(answer.strip()) > 0, 'AI 回答了空字符或纯空格'

def check_contains(answer, expected): # 这个不用改，它本身就需要 2 个
    assert expected in answer, f"未找到预期关键字'{expected}'，实际回答: {answer}"

def check_length_less_than_30(answer, expected=None):
    assert len(answer.strip()) < 30, f'回答太长了，超过了30个字符，实际长度:{len(answer)}'

def check_json_fields(answer, expected):
    type_map = {
        "string": str,
        "integer": int,
        "boolean": bool,
    }

    assert isinstance(expected, dict) and expected, "必须配置字段及类型"
    assert all(t in type_map for t in expected.values()), "存在不支持的字段类型"

    try:
        data = json.loads(answer)
    except (TypeError, ValueError) as exc:
        raise AssertionError(f"回答不是合法 JSON：{answer}") from exc

    assert isinstance(data, dict), "JSON 顶层必须是对象"

    for field, type_name in expected.items():
        assert field in data, f"缺少字段：{field}"
        required_type = type_map[type_name]

        assert type(data[field]) is required_type, (
            f"字段 {field} 应为 {type_name}，"
            f"实际为 {type(data[field]).__name__}"
        )

def check_grounded_answer(answer, expected):
    assert isinstance(answer, str), "模型回答必须是字符串"
    assert isinstance(expected, str) and expected.strip(), (
        "用例必须配置非空的预期答案"
    )

    actual = answer.strip()
    expected_answer = expected.strip()

    assert actual == expected_answer, (
        f"回答与预期不一致："
        f"预期 {expected_answer!r}，实际 {actual!r}。"
        "请结合资料判断是措辞不合规、错误拒答，还是无依据作答。"
    )

def check_numbered_steps(answer, expected):
    assert isinstance(answer, str), "回答必须是字符串"
    assert type(expected) is int and expected > 0, "步骤数必须是正整数"

    lines = [
        line.strip()
        for line in answer.splitlines()
        if line.strip()
    ]

    assert len(lines) == expected, (
        f"要求 {expected} 行步骤，实际 {len(lines)} 行"
    )

    for number, line in enumerate(lines, start=1):
        pattern = rf"{number}\.\s*\S.*"
        assert re.fullmatch(pattern, line), (
            f"第 {number} 行应以 '{number}.' 开头，且包含步骤内容：{line}"
        )

RULE_MAP = {
    "not_empty": check_not_empty,
    "contains_expected": check_contains,
    "length_less_than_30": check_length_less_than_30,
    "json_fields": check_json_fields,
    "grounded_answer": check_grounded_answer,
    "numbered_steps": check_numbered_steps
}