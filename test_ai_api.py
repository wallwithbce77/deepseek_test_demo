import pytest
test_cases = [
    ("1+1等于几？", ["2",'二']),
    ("中国的首都是哪里？", ["北京","Beijing"]),
    ("地球是圆的还是平的？", ["圆", "球", "椭球"])
]
@pytest.mark.parametrize('question,expect_keywords', test_cases)
def test_aichat(api_session,question,expect_keywords):
    url='https://api.deepseek.com/chat/completions'
    payload = \
        {'model':'deepseek-v4-flash',
         "messages": [{"role": "user", "content": question}],
         'temperature':0.7}
    response = api_session.post(url, json=payload, timeout=30)
    assert response.status_code == 200
    ai_answer = response.json()['choices'][0]['message']['content']
    assert any(keyword in ai_answer for keyword in expect_keywords), \
        f"AI 的回答里没有找到预期关键字 {expect_keywords}，实际回答: {ai_answer}"
def test_invalid_model(api_session):
    url = 'https://api.deepseek.com/chat/completions'
    payload = {
        'model': 'this-model-does-not-exist',
        'messages': [{"role": "user", "content": "你好"}]
    }
    response = api_session.post(url, json=payload)
    assert response.status_code == 400
    assert "error" in response.json()


def test_api_performance(api_session):
    url = 'https://api.deepseek.com/chat/completions'
    payload = {
        'model': 'deepseek-v4-flash',
        'messages': [{"role": "user", "content": "请回复'收到'两个字"}]
    }
    response = api_session.post(url, json=payload, timeout=30)
    cost_time = response.elapsed.total_seconds()
    print(f"\n本次请求耗时: {cost_time} 秒")
    assert cost_time < 10.0, f"接口响应过慢，耗时 {cost_time} 秒"
