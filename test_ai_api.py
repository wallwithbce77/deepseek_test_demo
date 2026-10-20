import pytest
import logging
import os
import json

current_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(current_dir, 'test_data.json')
with open(data_path, 'r', encoding='utf-8') as f:
    test_cases = json.load(f)

@pytest.mark.parametrize("case", test_cases,ids=[c['id'] for c in test_cases])
def test_aichat(api_session, case):
    question = case['question']
    expected=case['expected']
    checks=case['checks']

    url='https://api.deepseek.com/chat/completions'
    payload= {
        'model':'deepseek-v4-flash',
        'messages':[{'role':'user','content':question}],
        'temperature':0.7
    }

    logging.info(f'[{case["id"]}]开始测试|问题:{question}')

    response = api_session.post(url, json=payload,timeout=30)
    assert response.status_code == 200,f'接口报错:{response.text}'

    ai_answer = response.json()['choices'][0]['message']['content']
    logging.info(f'[{case["id"]}]AI回答:{ai_answer}')

    if 'not_empty' in checks:
        assert len(ai_answer)>0,'AI回答了空字符'
    if 'contains_expected' in checks:
        assert expected in ai_answer,f"未找到预期关键字'{expected}',实际回答: {ai_answer}"
    if 'length_less_than_30' in checks:
        assert len(ai_answer)<30,f'回答太长了，超过了30个字符，实际长度:{len(ai_answer)}'
    if 'is_json_format' in checks:
        try:
            json.loads(ai_answer)
        except ValueError:
            pytest.fail(f'没有返回合法的json格式，实际回答:{ai_answer}')