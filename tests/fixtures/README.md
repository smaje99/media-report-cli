# Test Media Fixtures

`tests/fixtures/media/` is treated as an optional local fixture area for discovery and
artifact-planning tests. The directory is ignored by Git on purpose; this `README.md` stays tracked
so the fixture contract and source provenance remain documented.

Tests always copy media fixtures into `tmp_path` before writing any outputs. If local media is not
present, the media-dependent scanner and CLI tests are skipped instead of failing.

## Current local sample set

The current local layout used by the tests is:

- `media/single/`
  - one or more supported media files; the tests prefer `profile_spanish.webm`, then
    `meeting_audio.wav`, then `meeting_video.mp4`, and otherwise use the first supported file found
  - current local examples:
    - `profile_spanish.webm`
    - `Entrevista_a_POLCEC.wav`
- `media/recursive/`
  - any mix of supported media files plus unsupported files such as `notes.txt`
  - current local examples:
    - `root_spanish_phrase.ogg`
    - `nested/child_sentence.mp4`
    - `nested/field_profile_spanish.webm`
    - `nested/Audio_Entrevista_Maximiliano_Perea.wav`
    - `nested/EntrevistaRichard_Stallman.ogg`
    - `notes.txt`

## Provenance

Known upstream sources for the current local samples:

| Local filename | Upstream source | License |
| --- | --- | --- |
| `profile_spanish.webm` | `I Am CDC - Nelly Mejia - (Español).webm` on Wikimedia Commons: <https://commons.wikimedia.org/wiki/File:I_Am_CDC_-_Nelly_Mejia_-_(Espa%C3%B1ol).webm> | Public domain (CDC / U.S. federal government work) |
| `field_profile_spanish.webm` | `I Am CDC - Eduardo O'Neill - Spanish.webm` on Wikimedia Commons: <https://commons.wikimedia.org/wiki/File:I_Am_CDC_-_Eduardo_O%27Neill_-_Spanish.webm> | Public domain (CDC / U.S. federal government work) |
| `child_sentence.mp4` | CDC low-res MP4 linked from Wikimedia Commons page `2 años - Dice frases de 2 a 4 palabras.webm`: <https://commons.wikimedia.org/wiki/File:2_a%C3%B1os_-_Dice_frases_de_2_a_4_palabras.webm> | Public domain (CDC / U.S. federal government work) |
| `root_spanish_phrase.ogg` | `Idioma espanol-castellano.ogg` on Wikimedia Commons: <https://commons.wikimedia.org/wiki/File:Idioma_espanol-castellano.ogg> | Public domain |
| `EntrevistaRichard_Stallman.ogg` | Wikimedia Commons: <https://commons.wikimedia.org/wiki/File:EntrevistaRichard_Stallman.ogg> | CC BY 2.5 |
| `Audio_Entrevista_Maximiliano_Perea.wav` | Wikimedia Commons category listing: <https://commons.wikimedia.org/wiki/Category:Audio_files_in_Spanish> | Review the specific file page before committing or redistributing |
| `Entrevista_a_POLCEC.wav` | Wikimedia Commons category listing: <https://commons.wikimedia.org/wiki/Category:Audio_files_in_Spanish> | Review the specific file page before committing or redistributing |

## Curation rules

- Keep media optional and local unless there is a strong reason to version it.
- Prefer filenames that are ASCII and stable when you rename or curate a smaller set.
- If you add or replace a sample, update this file with source URL and license before sharing it.
- If a sample is large, consider storing a shorter derivative locally for tests instead of the full
  original.
