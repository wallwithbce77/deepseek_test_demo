import os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-v4-flash"
TIMEOUT = 60