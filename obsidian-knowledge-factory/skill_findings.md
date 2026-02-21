# Skill Findings

## Reusable from legacy script
- Text/PDF reader pattern
- Header cleanup and regeneration
- Category mapping behavior
- Similarity-based dedupe scan
- Archive-after-success rule

## Replaced components
- n8n disassemble webhook -> local `disassembler.py`
- n8n upgrade webhook -> local `merger.py`

## Key constraints
- Keep data loss impossible during merge failures.
- Keep source traceability in each note.
