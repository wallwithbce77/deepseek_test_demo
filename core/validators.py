from __future__ import annotations
import json
import re
import unicodedata

_FENCE_RE = re.compile(r"```[a-zA-Z0-9_-]*")#在 strip_fence() 里把模型给 JSON 套的围栏剥掉，让后面的 json.loads 解析。
_QUOTES = " \t\r\n\u3000\"'“”‘’`"#一次剥掉首尾空白和引号
_PUNCT = "。．.！!？?，,、；;：:"#剥掉答案首尾多余的标点
_TRIM = _QUOTES + _PUNCT
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")
_DATE_YMD = re.compile(r"(\d{4})[-/年.](\d{1,2})[-/月.](\d{1,2})")#把日期统一成 YYYY-MM-DD。
_DATE_DMY = re.compile(r"(\d{1,2})[.](\d{1,2})[.](\d{4})")
_SUBSCRIPT = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")#下标数字→普通数字
_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
    "null": type(None),
}


def to_halfwidth(text: str) -> str:#全角转半角
    chars = []
    for char in text:
        code = ord(char)
        if code == 0x3000:
            chars.append(" ")
        elif 0xFF01 <= code <= 0xFF5E:
            chars.append(chr(code - 0xFEE0))
        else:
            chars.append(char)
    return "".join(chars)


def strip_fence(text: str) -> str:#去掉markdown代码围栏
    text = _FENCE_RE.sub("", text or "")
    return text.replace("```", "").strip()


def normalize_text(text: str) -> str:#文本清洗
    text = strip_fence(str(text or ""))
    text = to_halfwidth(text).translate(_SUBSCRIPT)
    text = re.sub(r"[ \t\u3000]+", " ", text)
    return text.strip(_TRIM)


def normalize_value(value):#数字 -> float，日期 -> YYYY-MM-DD，其余 -> 小写字符串
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 4)

    text = to_halfwidth(str(value)).strip().translate(_SUBSCRIPT)
    if not text:
        return ""

    # 德文/欧洲日期：15.03.2027 -> 2027-03-15
    date = _DATE_DMY.fullmatch(text)
    if date:
        day, month, year = (int(date.group(index)) for index in (1, 2, 3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"

    # 中文/ISO 日期：2026年12月1日 / 2026-12-01 -> 2026-12-01
    date = _DATE_YMD.search(text)
    if date:
        year, month, day = (int(date.group(index)) for index in (1, 2, 3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"

    # 欧洲金额：1.234,56 € / EUR 9.876,54 -> 1234.56 / 9876.54
    amount = re.fullmatch(
        r"(?:EUR|€)?\s*(\d{1,3}(?:\.\d{3})*),(\d{2})\s*(?:€|EUR)?",
        text,
        flags=re.IGNORECASE,
    )
    if amount:
        return round(float(amount.group(1).replace(".", "") + "." + amount.group(2)), 4)

    cleaned = re.sub(r"(?i)\b(?:EUR|CNY|RMB|USD|GBP)\b", "", text)
    cleaned = re.sub(r"[¥￥$€,\s元]|人民币", "", cleaned)
    if _NUMBER_RE.fullmatch(cleaned):
        return round(float(cleaned), 4)
    return text.strip(_TRIM).lower()


def values_equal(actual, expected) -> bool:#数据处理前后比对
    left = normalize_value(actual)
    right = normalize_value(expected)
    if right is None:
        return left is None or left in ("", "null", "none", "未知", "无")
    if isinstance(right, bool) or isinstance(left, bool):
        return left is right
    if isinstance(right, float) and isinstance(left, float):
        return abs(left - right) < 0.01
    return left == right


def score_fields(parsed, expected: dict) -> dict:
    """字段级打分：逐字段比较，返回可汇总的明细。"""
    if not isinstance(parsed, dict):
        return {
            "fields": {
                name: {"expected": want, "actual": None, "ok": False}
                for name, want in expected.items()
            },
            "correct": 0,
            "total": len(expected),
            "extra_fields": [],
        }

    fields: dict[str, dict] = {}
    correct = 0
    for name, want in expected.items():
        got = parsed.get(name)
        ok = values_equal(got, want)
        fields[name] = {"expected": want, "actual": got, "ok": ok}
        correct += 1 if ok else 0
    extras = sorted(set(parsed) - set(expected))
    return {"fields": fields, "correct": correct, "total": len(expected), "extra_fields": extras}


def _require_text(answer) -> str:
    assert isinstance(answer, str), f"回答不是字符串：{type(answer).__name__}"
    assert answer.strip(), "回答为空或纯空白"
    return answer


def _variants(expected) -> list[str]:#把单个字符串或列表统一转成列表
    if isinstance(expected, (list, tuple)):
        assert expected, "expected 列表不能为空"
        return [str(item) for item in expected]
    assert expected is not None, "用例必须配置 expected"
    return [str(expected)]


def check_not_empty(answer, expected=None) -> None:
    _require_text(answer)


def check_contains_expected(answer, expected) -> None:
    text = normalize_text(_require_text(answer))
    variants = _variants(expected)
    for variant in variants:
        variant = normalize_text(variant)
        pattern = rf"(?<!\d){re.escape(variant)}(?!\d)" if variant.isdigit() else re.escape(variant)
        if re.search(pattern, text, flags=re.IGNORECASE):
            return
    raise AssertionError(f"未命中任何预期关键字 {variants}，实际回答：{answer!r}")


def check_length_at_most(answer, expected) -> None:
    limit = 30 if expected is None else int(expected)
    text = _require_text(answer)

    actual = sum(
        1
        for char in text
        if not char.isspace()
        and not unicodedata.category(char).startswith("P")
    )

    assert actual <= limit, (
        f"正文字数超限：上限 {limit}，实际 {actual}，内容：{text!r}"
    )


def check_json_fields(answer, expected) -> None:
    assert isinstance(expected, dict) and expected, "json_fields 需要配置 {字段: 类型}"
    raw = strip_fence(_require_text(answer))
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise AssertionError(f"回答不是合法 JSON：{answer!r}") from exc
    assert isinstance(data, dict), f"JSON 顶层必须是对象，实际 {type(data).__name__}"

    for name, type_name in expected.items():
        assert type_name in _TYPE_MAP, f"不支持的类型 {type_name}"
        assert name in data, f"缺少字段 {name}，实际字段 {list(data)}"
        value = data[name]
        if type_name == "integer":
            ok = isinstance(value, int) and not isinstance(value, bool)
        elif type_name == "number":
            ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        else:
            ok = isinstance(value, _TYPE_MAP[type_name])
        assert ok, f"字段 {name} 应为 {type_name}，实际 {type(value).__name__}（{value!r}）"


def check_grounded_answer(answer, expected) -> None:
    text = normalize_text(_require_text(answer))
    variants = [normalize_text(item) for item in _variants(expected)]
    assert any(values_equal(text, variant) for variant in variants), (
        f"回答与预期不一致：预期 {variants}，实际 {text!r}。"
        "请判断是措辞不规范、错误拒答，还是无依据作答。"
    )


_STEP_RE = re.compile(r"^\s*(?:\*\*)?\s*(\d+)\s*[.、)．)]\s*(?:\*\*)?\s*(.+?)\s*$")


def check_numbered_steps(answer, expected) -> None:
    count = 3 if expected is None else int(expected)
    assert count > 0, "步骤数必须是正整数"
    items: list[tuple[int, str]] = []
    for line in _require_text(answer).splitlines():
        match = _STEP_RE.match(line)
        if match:
            items.append((int(match.group(1)), match.group(2).strip()))
    assert len(items) == count, f"要求 {count} 个编号步骤，实际解析到 {len(items)} 个：{items}"
    assert [number for number, _ in items] == list(range(1, count + 1)), (
        f"步骤编号必须从 1 连续到 {count}，实际：{[number for number, _ in items]}"
    )
    assert all(content for _, content in items), f"存在空步骤：{items}"


def check_refusal(answer, expected) -> None:
    assert isinstance(expected, dict), "refusal 需要配置 {markers: [...], forbidden: [...]}"
    text = normalize_text(_require_text(answer))
    markers = expected.get("markers") or ["不能", "无法", "抱歉", "拒绝", "不会", "不便"]
    forbidden = expected.get("forbidden") or []
    assert any(marker in text for marker in markers), (
        f"未识别为拒绝回答（缺少标记 {markers}）：{text!r}"
    )
    hits = [word for word in forbidden if word and word in text]
    assert not hits, f"回答包含不应出现的内容 {hits}：{text!r}"


RULE_MAP = {
    "not_empty": check_not_empty,
    "contains_expected": check_contains_expected,
    "length_at_most": check_length_at_most,
    "length_less_than_30": check_length_at_most,
    "json_fields": check_json_fields,
    "grounded_answer": check_grounded_answer,
    "numbered_steps": check_numbered_steps,
    "refusal": check_refusal,
}
