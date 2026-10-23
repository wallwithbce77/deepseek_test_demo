import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import API_KEY, BASE_URL, MODEL_NAME, TIMEOUT

class DeepseekClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'})

        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def chat(self, question):
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": question}]
        }
        response = self.session.post(BASE_URL, json=payload, timeout=TIMEOUT)
        return response