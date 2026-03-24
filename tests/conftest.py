import pytest

from cicd_agent.config import get_settings

_SETTINGS_ENV_VARS = [
    "REGISTRY_TYPE",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GCR_PROJECT_ID",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_DEFAULT_REGION",
    "DOCKER_HOST",
    "DEPLOY_SSH_KEY_PATH",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "LLM_MODEL",
    "MAX_RETRIES_PER_STEP",
    "MAX_TOTAL_RETRIES",
]


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def clean_env(monkeypatch):
    """Settings 관련 환경변수를 모두 제거하여 기본값 테스트를 격리"""
    for var in _SETTINGS_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
