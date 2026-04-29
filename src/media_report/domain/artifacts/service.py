from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from media_report.core.constants import ARTIFACT_SUFFIX
from media_report.core.errors import ArtifactConflictError
from media_report.domain.artifacts.entities import ArtifactPlan, PipelineMetadata, PipelineStage
from media_report.domain.media.entities import MediaSource


class ArtifactPlanner:
    def prepare(self, media_path: Path, overwrite: bool) -> ArtifactPlan:
        root_dir = media_path.parent / f"{media_path.stem}{ARTIFACT_SUFFIX}"
        if root_dir.exists() and not overwrite:
            raise ArtifactConflictError(
                f"Artifact directory already exists for '{media_path.name}': {root_dir}. "
                "Use --overwrite to reuse it."
            )
        root_dir.mkdir(parents=True, exist_ok=True)
        return ArtifactPlan(
            root_dir=root_dir,
            metadata_json=root_dir / "metadata.json",
            pipeline_log=root_dir / "pipeline.log",
            audio_extracted=root_dir / "audio_extracted.wav",
            audio_normalized=root_dir / "audio_normalized.wav",
            transcript_raw=root_dir / "transcript_raw.txt",
            transcript_segments=root_dir / "transcript_segments.json",
            transcript_clean=root_dir / "transcript_clean.md",
            prompt_used=root_dir / "prompt_used.md",
            llm_response_raw=root_dir / "llm_response_raw.txt",
            report_markdown=root_dir / "report.md",
            report_pdf=root_dir / "report.pdf",
        )

    def bootstrap_metadata(
        self,
        source: MediaSource,
        artifact_plan: ArtifactPlan,
        template_name: str,
        llm_provider: str,
        llm_model: str,
        output_format: str,
    ) -> PipelineMetadata:
        stages = {
            stage.value: {
                "status": "planned",
                "resumable": True,
            }
            for stage in PipelineStage
        }
        payload = {
            "schema_version": 1,
            "generated_at": datetime.now(UTC).isoformat(),
            "source": {
                "path": str(source.path),
                "kind": source.kind.value,
            },
            "artifacts": {
                "root_dir": str(artifact_plan.root_dir),
                "metadata_json": str(artifact_plan.metadata_json),
                "pipeline_log": str(artifact_plan.pipeline_log),
                "audio_extracted": str(artifact_plan.audio_extracted),
                "audio_normalized": str(artifact_plan.audio_normalized),
                "transcript_raw": str(artifact_plan.transcript_raw),
                "transcript_segments": str(artifact_plan.transcript_segments),
                "transcript_clean": str(artifact_plan.transcript_clean),
                "prompt_used": str(artifact_plan.prompt_used),
                "llm_response_raw": str(artifact_plan.llm_response_raw),
                "report_markdown": str(artifact_plan.report_markdown),
                "report_pdf": str(artifact_plan.report_pdf),
            },
            "workflow": {
                "template_name": template_name,
                "llm_provider": llm_provider,
                "llm_model": llm_model,
                "output_format": output_format,
            },
            "stages": stages,
        }
        return PipelineMetadata(payload=payload)

    def write_metadata(self, metadata: PipelineMetadata) -> None:
        target = Path(metadata.payload["artifacts"]["metadata_json"])
        target.write_text(json.dumps(metadata.payload, indent=2), encoding="utf-8")

    def initialize_log(self, artifact_root: Path) -> None:
        log_path = artifact_root / "pipeline.log"
        if not log_path.exists():
            log_path.write_text("media-report bootstrap initialized\n", encoding="utf-8")
