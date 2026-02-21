---
name: obsidian-knowledge-factory
description: Use when users need to clean, atomize, deduplicate, and archive mixed text files into an Obsidian vault using a local Python pipeline with an OpenAI-compatible API, without n8n.
---

# Obsidian Knowledge Factory

## Overview
This skill runs a local file-processing pipeline for Obsidian knowledge ingestion. It replaces webhook workflows with Python modules while keeping traceability, dedupe safety, and archive discipline.

## When to Use
- Large batches of notes, articles, transcripts, or PDFs must be converted into atomic notes.
- Existing content has noisy formatting and inconsistent structure.
- You need deterministic output schema and failure queues.
- n8n is unavailable or intentionally removed from the workflow.

## Inputs and Outputs
- Input folder: `<vault_path>/<inbox_name>`
- Output folders: category folders in the same vault
- Archive folder: `<vault_path>/<archive_name>`
- Failed queue: `<vault_path>/inbox/Failed`
- Output schema per atom:
  - `category`
  - `filename`
  - `content`
  - `source`
  - `tags`
  - `confidence`

## Execution Flow
1. Scan inbox for `md/txt/pdf`.
2. Read source text.
3. Call OpenAI-compatible model for atomization.
4. Parse and validate JSON output.
5. Deduplicate and merge safely.
6. Write notes and archive source file.

## Red Flags
- Missing `OPENAI_API_KEY` or invalid `OPENAI_BASE_URL`.
- Workflow role prompt exists but API mode is not enabled.
- Model output cannot be parsed into JSON after cleanup.
- Merge result is empty.
- Source file is archived but no note was written.

## Verification Checklist
- Run once: `python engine/main.py --once`
- Check summary includes scanned/succeeded/failed/merged/archived.
- Confirm failed payloads exist in `inbox/Failed` when parse errors occur.
- Confirm archived source appears in archive folder only after success.
