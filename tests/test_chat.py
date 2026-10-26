from __future__ import annotations
import json
import pytest
from core import config, dataset
from core.validators import RULE_MAP, strip_fence

CASES = dataset.chat_cases()
QUESTION = '只输出一个 JSON 对象：{"status": "ok"}。不要代码块、不要任何解释。'


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_chat_case(api_client, run_ctx, case):
    latency, tokens, status, detail = 0.0, 0, "failed", ""
    try:
        fmt = {"type": "json_object"} if "json_fields" in case["checks"] else None
        result = api_client.ask(
            case["question"], system=case.get("system"), response_format=fmt,
            case_id=case["id"], max_tokens=case.get("max_tokens"),
        )
        latency, tokens = result.elapsed, result.total_tokens
        assert result.status_code == 200, f"HTTP {result.status_code}：{result.error_message}"
        assert result.content, "模型返回空内容"
        assert result.finish_reason != "length", "输出被截断"
        assert result.elapsed <= config.MAX_LATENCY_S, f"响应过慢：{result.elapsed:.2f}s"
        for rule in case["checks"]:
            RULE_MAP[rule](result.content, case.get("expected"))
        status = "passed"
    except AssertionError as exc:
        detail = str(exc)[:300]
        if case.get("known_issue"):
            pytest.xfail(f"已知缺陷 {case['known_issue']}：{detail}")
        raise
    finally:
        run_ctx.add_case(case["id"], case["category"], status, latency, tokens, detail)


@pytest.mark.parametrize("index", range(config.STABILITY_RUNS), ids=[f"R{i+1}" for i in range(config.STABILITY_RUNS)])
def test_json_output_stable(api_client, run_ctx, index):
    result = api_client.ask(QUESTION, case_id="STABILITY", response_format={"type": "json_object"})
    status, detail = "failed", ""
    try:
        assert result.status_code == 200, f"HTTP {result.status_code}"
        data = json.loads(strip_fence(result.content))
        assert isinstance(data, dict) and data.get("status") == "ok", f"内容不符：{data!r}"
        status = "passed"
    except AssertionError as exc:
        detail = str(exc)[:300]
        raise
    finally:
        run_ctx.add_case(f"STAB-{index + 1}", "稳定性", status, result.elapsed, result.total_tokens, detail)
