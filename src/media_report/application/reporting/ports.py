from __future__ import annotations

from typing import Protocol

from media_report.application.reporting.models import (
  GenerateReportRequest,
  GenerateReportResult,
  RenderPromptRequest,
  RenderPromptResult,
)


class PromptRenderUseCase(Protocol):
  """Application contract for prompt rendering over existing artifacts."""

  def render_prompt(self, request: RenderPromptRequest) -> RenderPromptResult:
    """Render and persist a reporting prompt for a single artifact root."""


class ReportGenerationUseCase(Protocol):
  """Application contract for full report generation over existing artifacts."""

  def generate_report(self, request: GenerateReportRequest) -> GenerateReportResult:
    """Render the reporting prompt and generate report artifacts."""
