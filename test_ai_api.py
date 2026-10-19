import pytest
test_cases = [
    ("1+1等于几？", "2"),
    ("中国的首都是哪里？", "北京"),
    ("地球是圆的还是平的？", "圆")
]
@pytest.mark.parametrize('question,expect_keyword', test_cases)
def test_aichat(api_session,question,expect_keyword):
    url='https://api.deepseek.com/chat/completions'
    payload = \
        {'model':'deepseek-v4-flash',
         "messages": [{"role": "user", "content": question}],
         'temperature':0.7}
    response = api_session.post(url, json=payload, timeout=30)
    assert response.status_code == 200
    ai_answer = response.json()['choices'][0]['message']['content']
    assert expect_keyword in ai_answer, f"AI 的回答里没有找到关键字 '{expect_keyword}'，实际回答: {ai_answer}"

