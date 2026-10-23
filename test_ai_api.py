import pytest
import logging
import os
import json
from validators import RULE_MAP
from config import BASE_URL, MODEL_NAME

current_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(current_dir, 'test_data.json')
with open(data_path, 'r', encoding='utf-8') as f:
    test_cases = json.load(f)

@pytest.mark.parametrize("case", test_cases, ids=[c['id'] for c in test_cases])
def test_aichat(api_client, case):
    question = case['question']
    expected = case.get('expected', "")
    checks = case['checks']

    logging.info(f'[{case["id"]}]开始测试|问题:{question}')
    response = api_client.chat(question)

    cost_time = response.elapsed.total_seconds()

    assert response.status_code == 200, f'接口报错:{response.text}'

    ai_answer = response.json()['choices'][0]['message']['content']
    logging.info(f'[{case["id"]}]AI回答:{ai_answer} | 耗时: {cost_time:.2f}s')

    for rule_name in checks:
      assert rule_name in RULE_MAP,f'发生错误，不存在规则{rule_name}'
      RULE_MAP[rule_name](ai_answer, expected)


def test_json_stability(api_client):
    question = "请严格输出一段JSON，格式必须为 {\"status\": \"ok\"}"
    success_count = 0
    total_runs = 5

    for i in range(total_runs):
        response = api_client.chat(question)
        ai_answer = response.json()['choices'][0]['message']['content']

        try:
            parsed = json.loads(ai_answer)
            if parsed.get("status") == "ok":
                success_count += 1
        except json.JSONDecodeError:
            logging.error(f"第 {i + 1} 次失败，返回了非 JSON 格式: {ai_answer}")

    success_rate = success_count / total_runs
    logging.info(f"【稳定性报告】JSON格式成功率: {success_rate * 100}%")
    assert success_rate >= 0.8, f"格式稳定性太差！成功率仅 {success_rate * 100}%"