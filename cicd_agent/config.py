import sys
from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", frozen=True)

    # --- Registry ---
    registry_type: Literal["gcr", "ecr"] = "gcr"

    # --- GCR ---
    google_application_credentials: str | None = None
    gcr_project_id: str | None = None

    # --- AWS/ECR ---
    aws_access_key_id: str | None = None
    aws_secret_access_key: SecretStr | None = None
    aws_default_region: str = "ap-northeast-2"

    # --- Docker ---
    docker_host: str = (
        "npipe:////./pipe/docker_engine"
        if sys.platform == "win32"
        else "unix:///var/run/docker.sock"
    )

    # --- SSH (선택) ---
    deploy_ssh_key_path: str | None = None

    # --- LLM ---
    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    llm_model: str = "anthropic/claude-sonnet-4-20250514"

    # --- Execution ---
    max_retries_per_step: int = 2
    max_total_retries: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
