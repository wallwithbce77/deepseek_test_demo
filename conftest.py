import pytest
from client import DeepseekClient

@pytest.fixture(scope="session")
def api_client():
    client=DeepseekClient()
    yield client
    client.session.close()