from __future__ import annotations

import re
from collections.abc import Sequence
from urllib.parse import urlsplit, urlunsplit

_BEARER_TOKEN_PATTERN = re.compile(r"(?i)\b(bearer)\s+([^\s,;]+)")


def redact_secret(value: str | None) -> str:
  if not value:
    return "<unset>"
  return "***" if len(value) <= 6 else f"{value[:2]}***{value[-2:]}"


def redact_text(text: str, *, secrets: Sequence[str] = ()) -> str:
  redacted = text
  for secret in secrets:
    if secret:
      redacted = redacted.replace(secret, "***")

  redacted = _BEARER_TOKEN_PATTERN.sub(r"\1 ***", redacted)
  return _redact_urls_with_credentials(redacted)


def _redact_urls_with_credentials(text: str) -> str:
  tokens = text.split()
  redacted_tokens: list[str] = []
  redacted_tokens.extend(_redact_url_token(token) for token in tokens)
  return " ".join(redacted_tokens)


def _redact_url_token(token: str) -> str:
  prefix = ""
  suffix = ""
  candidate = token

  while candidate and candidate[0] in "\"'(<[{":
    prefix += candidate[0]
    candidate = candidate[1:]
  while candidate and candidate[-1] in "\"'),.;:>]}":
    suffix = candidate[-1] + suffix
    candidate = candidate[:-1]

  if "://" not in candidate or "@" not in candidate:
    return token

  try:
    parts = urlsplit(candidate)
  except ValueError:
    return token

  if parts.username is None or parts.password is None or parts.hostname is None:
    return token

  port = f":{parts.port}" if parts.port is not None else ""
  netloc = f"***:***@{parts.hostname}{port}"
  return (
    prefix + urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment)) + suffix
  )
