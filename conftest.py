import pytest
import os
import requests
from dotenv import load_dotenv
load_dotenv()
@pytest.fixture(scope="session")
def api_session():
    api_key=os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError('找不到环境变量')
    session=requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    })
    yield session
    session.close()