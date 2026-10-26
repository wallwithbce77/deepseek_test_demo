from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

API_KEY = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/chat/completions")
MODEL_NAME = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
TIMEOUT = float(os.getenv("DEEPSEEK_TIMEOUT", "60"))
TEMPERATURE = float(os.getenv("DEEPSEEK_TEMPERATURE", "0"))
MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", "1024"))

# 离线模式
USE_FAKE = os.getenv("USE_FAKE", "").strip().lower() in {"1", "true", "yes"} or not API_KEY
FAKE_ERROR_RATE = float(os.getenv("FAKE_ERROR_RATE", "0"))
FAKE_SEED = int(os.getenv("FAKE_SEED", "7"))

DATA_DIR = ROOT / "data"
ARTIFACT_DIR = Path(os.getenv("ARTIFACT_DIR") or (ROOT / "artifacts"))

MAX_LATENCY_S = float(os.getenv("MAX_LATENCY_S", "20"))
STABILITY_RUNS = int(os.getenv("STABILITY_RUNS", "5"))

#质量门禁汇总
THRESHOLDS = {
    "json_valid_rate": float(os.getenv("GATE_JSON_VALID_RATE", "0.95")),
    "field_accuracy": float(os.getenv("GATE_FIELD_ACCURACY", "0.85")),
    "p95_latency_s": float(os.getenv("GATE_P95_LATENCY_S", "15")),
}
