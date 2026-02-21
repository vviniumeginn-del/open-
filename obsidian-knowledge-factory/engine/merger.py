def merge_content(old_content: str, new_content: str) -> tuple[str, bool]:
    """Return (merged_content, merged_flag). Never return empty content."""
    old = (old_content or "").strip()
    new = (new_content or "").strip()

    if not old:
        return new, False
    if not new:
        return old, False
    if old == new:
        return old, True
    if new in old:
        return old, True
    if old in new:
        return new, True

    old_lines = [line for line in old.splitlines() if line.strip()]
    merged_lines = list(old_lines)
    existing = set(old_lines)
    for line in new.splitlines():
        if line.strip() and line not in existing:
            merged_lines.append(line)
            existing.add(line)

    merged = "\n".join(merged_lines).strip()
    if not merged:
        merged = (old + "\n\n---\n\n" + new).strip()
    return merged, True
