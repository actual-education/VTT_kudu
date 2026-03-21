from pathlib import Path

from pydantic_settings import BaseSettings

ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    USE_MOCKS: bool = True
    DATABASE_URL: str = "sqlite:///./avce.db"
    SECRET_KEY: str = "change-me-in-production"

    YOUTUBE_API_KEY: str = ""
    YT_DLP_BINARY: str = "yt-dlp"
    FFMPEG_BINARY: str = "ffmpeg"
    VIDEO_CACHE_DIR: str = "/tmp/avce_videos"
    FRAME_OUTPUT_DIR: str = "/tmp/avce_frames"

    TESSERACT_CMD: str = "tesseract"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-10-21"

    YOUTUBE_OAUTH_CLIENT_SECRETS_FILE: str = ""
    YOUTUBE_OAUTH_TOKEN_FILE: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    AUTH_PASSWORD: str = ""
    AUTH_COOKIE_NAME: str = "avce_auth"
    AUTH_SESSION_TTL_HOURS: int = 24
    AUTH_COOKIE_SECURE: bool = False

    REQUIRE_MODEL_SUCCESS: bool = False
    AI_COST_INPUT_PER_1M_TOKENS: float = 0.0
    AI_COST_OUTPUT_PER_1M_TOKENS: float = 0.0
    MODEL_REQUEST_TIMEOUT_SECONDS: float = 60.0
    MODEL_MAX_RETRIES: int = 0
    DESCRIPTION_MODEL_MAX_SEGMENTS: int = 30

    SEGMENT_MERGE_MAX_GAP_SECONDS: float = 1.5
    SEGMENT_MERGE_OCR_SIMILARITY_THRESHOLD: float = 0.85
    SEGMENT_MERGE_DESCRIPTION_SIMILARITY_THRESHOLD: float = 0.75

    model_config = {"env_file": str(ROOT_ENV_FILE), "env_file_encoding": "utf-8"}


settings = Settings()
