from media_report.core.redaction import redact_secret, redact_text


def test_redact_secret_masks_middle_characters() -> None:
  assert redact_secret("sk-example-secret") == "sk***et"


def test_redact_text_masks_bearer_tokens_explicit_secrets_and_url_credentials() -> None:
  text = (
    "Authorization: Bearer sk-example-secret "
    "https://user:pass@example.invalid/v1 "
    "raw=sk-example-secret"
  )

  redacted = redact_text(text, secrets=("sk-example-secret",))

  assert "sk-example-secret" not in redacted
  assert "Bearer ***" in redacted
  assert "https://***:***@example.invalid/v1" in redacted
