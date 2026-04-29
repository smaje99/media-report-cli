from pathlib import Path

from media_report.core.settings import AppSettings, load_settings, write_default_config


def test_load_settings_merges_file_and_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    config_path = write_default_config()
    config_path.write_text(
        """
[llm]
provider = "ollama"
model = "llama3.2"

[openai]
api_key = "file-secret"
base_url = "https://example.invalid/v1"
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("MEDIA_REPORT_LLM_MODEL", "gpt-4.1-mini")

    settings = load_settings()

    assert settings.llm_provider == "ollama"
    assert settings.llm_model == "gpt-4.1-mini"
    assert settings.openai_api_key == "file-secret"
    assert settings.openai_base_url == "https://example.invalid/v1"


def test_display_dict_redacts_secret() -> None:
    settings = AppSettings(openai_api_key="sk-example-secret")

    assert settings.to_display_dict()["openai_api_key"] == "sk***et"
