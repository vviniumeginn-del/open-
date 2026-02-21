# Obsidian Knowledge Factory

Local Python pipeline to ingest mixed files into an Obsidian vault without n8n.

## Features
- Inbox scanning for `.md`, `.txt`, `.pdf`, `.docx`, and common image formats
- LLM atomization via OpenAI-compatible API
- Optional prompt loading from your legacy workflow JSON (`Obsidian_Disassembler (2).json`)
- JSON cleanup and schema validation
- Similarity-based dedupe and safe merge
- Source archiving after successful processing
- Failed payload queue for debugging

## Supported Input Types
- Text: `.md`, `.txt`
- Documents: `.pdf`, `.docx` (`.doc` is not supported directly)
- Images (OCR): `.png`, `.jpg`, `.jpeg`, `.bmp`, `.webp`, `.tif`, `.tiff`

For image OCR, run the pipeline with a Python environment that has `paddleocr` installed (recommended: `D:\vivi\.venv310`).

## Multi-image article (important)
If one article spans multiple screenshots, name files with the same prefix and ordered suffix:

- `articleA_01.png`
- `articleA_02.png`
- `articleA_03.png`

The pipeline will treat them as one source item, OCR in order, concatenate text, then clean into knowledge notes.

## Chinese-readable filename mode
- The pipeline enforces Chinese-readable filenames by default.
- If the model returns non-Chinese or mojibake filenames, it auto-falls back to:
  - `<source>_条目NN_<timestamp>.md`
- Category mapping follows the `obsidian_n8n_sync.py` style (English labels mapped into Chinese folders).

## Bridge export to dontbesilent-OS
- Default for your current setup: `bridge_export_enabled: false` (cleaning system and creation system are separated).
- Enable in `engine/config.yaml` with `bridge_export_enabled: true`.
- The pipeline will copy each saved note into one of:
  - `核心概念库`
  - `金句库`
  - `爆款文稿库`
- Destination root is configurable with:
  - `bridge_os_root`
  - `bridge_material_root`

## Directory
```
obsidian-knowledge-factory/
  SKILL.md
  skill_plan.md
  skill_findings.md
  skill_progress.md
  references/
  examples/
  engine/
```

## Setup
1. Copy `.env.example` to `.env` and fill values.
2. Copy `config.example.yaml` to `config.yaml` and adjust paths.
3. Install dependencies:

```bash
pip install -r engine/requirements.txt
```

## Run

Single run:
```bash
python engine/main.py --once --config engine/config.yaml --env-file engine/.env
```

Important:
- With API credentials, the pipeline can use the role/prompt from `prompt_workflow_json` in config.
- If the primary key is exhausted, set backup credentials with `OPENAI_*_BACKUP`; the client auto-falls back once.

Daemon mode:
```bash
python engine/main.py --daemon --interval 600 --config engine/config.yaml --env-file engine/.env
```

## Expected Summary
Each run prints:
- `scanned`
- `succeeded`
- `failed`
- `merged`
- `archived`

## Troubleshooting
- Parse failures: check `<vault>/inbox/Failed/*.json`
- Network/API failures: check `<vault>/logs/network_error.log`
- Write failures: check `<vault>/logs/write_error.log`
