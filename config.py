import os

try:  # read settings from a .env file next to app.py
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "mysql+pymysql://root:@localhost/placement_db?charset=utf8mb4")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "0") == "1"  # set 1 behind HTTPS

    # --- AI assistant: any OpenAI-compatible API. Put these in .env; never commit your key ---
    OPENAI_API_KEY = (os.environ.get("GEMINI_API_KEY") or os.environ.get("CLEANAPIS_API_KEY")
                      or os.environ.get("AI_API_KEY") or os.environ.get("OPENAI_API_KEY")
                      or os.environ.get("AGENTROUTER_API_KEY", ""))
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "models/gemini-flash-lite-latest")
    OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL",
                                     "https://generativelanguage.googleapis.com/v1beta/openai/")
    OPENAI_REASONING_EFFORT = os.environ.get("OPENAI_REASONING_EFFORT", "")  # optional
    AI_RATE_LIMIT = int(os.environ.get("AI_RATE_LIMIT", "15"))  # messages per 10 min per user/IP
    AI_FALLBACK = os.environ.get("AI_FALLBACK", "1") == "1"      # answer from site data if AI fails
