# Workflow Context

## Pipeline Shape

1. Validate the input path.
2. Discover supported media files.
3. Create an artifact directory for each media file.
4. Extract audio when the source is video.
5. Normalize audio for transcription.
6. Transcribe and persist raw plus structured transcript data.
7. Clean and segment transcript text.
8. Render a prompt from a packaged template.
9. Generate a report through a configured LLM provider.
10. Convert Markdown to PDF.

## Artifact Policy

Each source file gets a sibling artifact directory named:

```text
<source_stem>_media_report/
```

Expected artifacts include:

- `metadata.json`
- `pipeline.log`
- `audio_extracted.wav`
- `audio_normalized.wav`
- `transcript_raw.txt`
- `transcript_segments.json`
- `transcript_clean.md`
- `prompt_used.md`
- `llm_response_raw.txt`
- `report.md`
- `report.pdf`

## Failure Handling

- Preserve upstream artifacts if a later stage fails.
- Keep stage status in metadata for future resume support.
- Never lose Markdown when PDF generation fails.
