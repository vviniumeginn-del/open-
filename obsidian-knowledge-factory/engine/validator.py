import ast
import json
import re
from datetime import datetime


REQUIRED_FIELDS = {"category", "filename", "content"}


def dirty_json_clean(text: str):
    cleaned = re.sub(r"```\w*\n", "", text).replace("```", "")
    match = re.search(r"(\[.*\])", cleaned, re.DOTALL)
    candidate = None
    if match:
        candidate = match.group(1)
    else:
        match_obj = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match_obj:
            candidate = f"[{match_obj.group(1)}]"
    if not candidate:
        return None

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    try:
        candidate_py = candidate.replace("true", "True").replace("false", "False").replace("null", "None")
        return ast.literal_eval(candidate_py)
    except Exception:  # noqa: BLE001
        return None


def validate_notes(raw_output: str, source_file: str):
    failures = []
    parsed = dirty_json_clean(raw_output)
    if parsed is None:
        return [], [{"error": "json_parse_error", "source_file": source_file, "raw": raw_output}]

    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return [], [{"error": "json_not_list", "source_file": source_file, "raw": raw_output}]

    validated = []
    now = datetime.now().isoformat(timespec="seconds")
    for idx, item in enumerate(parsed):
        if not isinstance(item, dict):
            failures.append({"error": "item_not_object", "index": idx, "item": item, "source_file": source_file})
            continue

        missing = sorted(list(REQUIRED_FIELDS - set(item.keys())))
        if missing:
            failures.append({
                "error": "schema_missing_field",
                "index": idx,
                "missing": missing,
                "item": item,
                "source_file": source_file,
            })
            continue

        note = dict(item)
        note["filename"] = str(note["filename"])
        note["source"] = note.get("source") or {}
        if not isinstance(note["source"], dict):
            note["source"] = {}
        note["source"].setdefault("file", source_file)
        note["source"].setdefault("platform", "unknown")
        note["source"].setdefault("import_time", now)
        note["tags"] = note.get("tags") if isinstance(note.get("tags"), list) else []
        try:
            conf = float(note.get("confidence", 0.6))
        except Exception:  # noqa: BLE001
            conf = 0.6
        note["confidence"] = max(0.0, min(1.0, conf))
        validated.append(note)

    return validated, failures
