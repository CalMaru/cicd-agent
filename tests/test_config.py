import pytest
from pydantic import SecretStr, ValidationError

from cicd_agent.config import Settings


def _make_settings(**kwargs) -> Settings:
    """테스트용 Settings 생성. .env 파일을 읽지 않음."""
    return Settings(_env_file=None, **kwargs)


class TestSettingsDefaults:
    def test_defaults_with_no_credentials(self, clean_env):
        settings = _make_settings()
        assert settings.registry_type == "gcr"
        assert settings.aws_default_region == "ap-northeast-2"
        assert settings.llm_model == "anthropic/claude-sonnet-4-20250514"
        assert settings.max_retries_per_step == 2
        assert settings.max_total_retries == 3
        assert settings.google_application_credentials is None
        assert settings.aws_access_key_id is None
        assert settings.deploy_ssh_key_path is None

    def test_docker_host_default_unix(self, clean_env):
        settings = _make_settings()
        assert "unix://" in settings.docker_host or "npipe://" in settings.docker_host


class TestSettingsRegistryType:
    def test_gcr(self):
        settings = _make_settings(registry_type="gcr")
        assert settings.registry_type == "gcr"

    def test_ecr(self):
        settings = _make_settings(registry_type="ecr")
        assert settings.registry_type == "ecr"

    def test_invalid_registry_type(self):
        with pytest.raises(ValidationError):
            _make_settings(registry_type="dockerhub")


class TestSettingsFrozen:
    def test_cannot_modify(self):
        settings = _make_settings()
        with pytest.raises(ValidationError):
            settings.registry_type = "ecr"


class TestSettingsSecretStr:
    def test_secret_not_exposed_in_str(self):
        settings = _make_settings(aws_secret_access_key="my-secret-key-12345")
        assert "my-secret-key-12345" not in str(settings.aws_secret_access_key)

    def test_secret_accessible_via_get_secret_value(self):
        settings = _make_settings(aws_secret_access_key="my-secret-key-12345")
        assert isinstance(settings.aws_secret_access_key, SecretStr)
        assert settings.aws_secret_access_key.get_secret_value() == "my-secret-key-12345"

    def test_llm_api_key_secret(self):
        settings = _make_settings(anthropic_api_key="sk-ant-12345678")
        assert "sk-ant-12345678" not in str(settings.anthropic_api_key)
        assert settings.anthropic_api_key.get_secret_value() == "sk-ant-12345678"
