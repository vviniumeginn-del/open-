# Workflow Schema

## Note Schema
```json
{
  "category": "03_Content Assets",
  "filename": "[Biz]_Example_Title.md",
  "content": "atomic note content",
  "source": {
    "file": "source.md",
    "platform": "xiaohongshu",
    "import_time": "2026-02-11T12:00:00"
  },
  "tags": ["tag1", "tag2"],
  "confidence": 0.82
}
```

## Processing Contract
- `category`, `filename`, `content` are required.
- `source`, `tags`, `confidence` are auto-filled if missing.
