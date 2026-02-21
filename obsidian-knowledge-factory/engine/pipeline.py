import json
import re
import shutil
from pathlib import Path

from disassembler import disassemble_text, force_json_array, load_prompt_from_workflow_json
from io_utils import (
    append_log,
    archive_file,
    clean_existing_header,
    dump_failed_payload,
    fallback_title,
    generate_header,
    has_chinese,
    is_readable_title,
    read_file_content,
    sanitize_filename,
    similarity_target,
)
from merger import merge_content
from validator import validate_notes


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}


class Pipeline:
    def __init__(self, config: dict, client):
        self.config = config
        self.client = client
        self.vault_path = Path(config["vault_path"])
        self.inbox_dir = self.vault_path / config.get("inbox_name", "inbox")
        self.archive_dir = self.vault_path / config.get("archive_name", "99_Archive")
        self.failed_dir = self.vault_path / config.get("failed_name", "inbox/Failed")
        self.log_dir = self.vault_path / config.get("log_dir_name", "logs")
        self.similarity_threshold = float(config.get("similarity_threshold", 0.9))
        self.mapping = config.get("category_mapping", {})
        self.system_prompt = None
        if bool(config.get("prefer_workflow_prompt", True)):
            self.system_prompt = load_prompt_from_workflow_json(config.get("prompt_workflow_json"))
        self.bridge_export_enabled = bool(config.get("bridge_export_enabled", False))
        self.bridge_os_root = Path(config.get("bridge_os_root", "")) if config.get("bridge_os_root") else None
        self.bridge_material_root = config.get("bridge_material_root", "01-内容生产/内容素材库")
        self.bridge_subfolder_map = config.get("bridge_subfolder_map", {})

    def process_once(self) -> dict:
        summary = {
            "scanned": 0,
            "succeeded": 0,
            "failed": 0,
            "merged": 0,
            "archived": 0,
            "saved_files": [],
            "merged_files": [],
        }
        self.inbox_dir.mkdir(parents=True, exist_ok=True)

        files = []
        for ext in (
            "*.md",
            "*.txt",
            "*.pdf",
            "*.docx",
            "*.png",
            "*.jpg",
            "*.jpeg",
            "*.bmp",
            "*.webp",
            "*.tif",
            "*.tiff",
        ):
            files.extend(self.inbox_dir.glob(ext))

        work_items = self._build_work_items(files)

        for item in work_items:
            item_paths = item["paths"]
            summary["scanned"] += len(item_paths)
            try:
                if len(item_paths) == 1:
                    print(f"[START] 清洗文件: {item_paths[0].name}")
                else:
                    names = ", ".join(p.name for p in item_paths)
                    print(f"[START] 清洗图片组({len(item_paths)}): {names}")

                content_parts = []
                for idx, path in enumerate(item_paths, start=1):
                    part = read_file_content(path)
                    if len(item_paths) > 1:
                        content_parts.append(f"[Page {idx}: {path.name}]\n{part}")
                    else:
                        content_parts.append(part)

                content = "\n\n".join(content_parts).strip()
                if not content.strip():
                    summary["failed"] += 1
                    print(f"[SKIP] 空内容: {item['source_name']}")
                    dump_failed_payload(self.failed_dir, {"error": "empty_source", "source_file": item["source_name"]})
                    continue

                raw = disassemble_text(self.client, content, Path(item["source_name"]), self.system_prompt)
                normalized_raw = force_json_array(raw)
                notes, failures = validate_notes(normalized_raw, item["source_name"])

                for failure in failures:
                    summary["failed"] += 1
                    print(f"[WARN] 解析失败: {failure.get('error', 'unknown_error')} ({item['source_name']})")
                    dump_failed_payload(self.failed_dir, failure)

                success_count = 0
                for idx, note in enumerate(notes, start=1):
                    note["__source_name"] = item["source_name"]
                    note["__index"] = idx
                    ok, merged, out_path = self._save_note(note)
                    if ok:
                        success_count += 1
                        summary["succeeded"] += 1
                        if out_path:
                            name = Path(out_path).name
                            if merged:
                                summary["merged_files"].append(name)
                            else:
                                summary["saved_files"].append(name)
                            self._bridge_export(Path(out_path), note)
                        if merged:
                            summary["merged"] += 1
                    else:
                        summary["failed"] += 1

                if success_count > 0:
                    for path in item_paths:
                        archive_file(path, self.archive_dir)
                        print(f"[ARCHIVE] {path.name}")
                    summary["archived"] += len(item_paths)
            except Exception as exc:  # noqa: BLE001
                summary["failed"] += 1
                print(f"[ERROR] 处理失败: {item['source_name']} -> {exc}")
                append_log(self.log_dir / "pipeline_error.log", f"{item['source_name']}: {exc}")

        return summary

    def _build_work_items(self, files: list[Path]) -> list[dict]:
        ordered = sorted(files, key=lambda p: p.name.lower())
        image_files = [p for p in ordered if p.suffix.lower() in IMAGE_SUFFIXES]
        other_files = [p for p in ordered if p.suffix.lower() not in IMAGE_SUFFIXES]

        items = [{"source_name": p.name, "paths": [p]} for p in other_files]

        grouped = {}
        single_images = []
        pattern = re.compile(r"^(?P<prefix>.+?)[-_](?:(?:p|part))?(?P<num>\d{1,3})$", re.IGNORECASE)
        pattern_paren = re.compile(r"^(?P<prefix>.+?)\s*\((?P<num>\d{1,3})\)$", re.IGNORECASE)

        for img in image_files:
            m = pattern.match(img.stem) or pattern_paren.match(img.stem)
            if not m:
                single_images.append(img)
                continue
            key = m.group("prefix")
            num = int(m.group("num"))
            grouped.setdefault(key, []).append((num, img))

        for key in sorted(grouped.keys(), key=lambda s: s.lower()):
            parts = sorted(grouped[key], key=lambda t: t[0])
            paths = [p for _, p in parts]
            if len(paths) == 1:
                items.append({"source_name": paths[0].name, "paths": paths})
            else:
                source_name = f"{key}__image_group_{len(paths)}.txt"
                items.append({"source_name": source_name, "paths": paths})

        for img in single_images:
            items.append({"source_name": img.name, "paths": [img]})

        return items

    def _save_note(self, note: dict) -> tuple[bool, bool, str | None]:
        try:
            category = self.mapping.get(note.get("category", "inbox/Unsorted"), note.get("category", "inbox/Unsorted"))
            raw_filename = str(note.get("filename", "AutoNote.md"))
            source_name = str(note.get("__source_name", "来源文档"))
            index = int(note.get("__index", 1))
            enforce_cn = bool(self.config.get("force_chinese_filename", True))

            if enforce_cn and not has_chinese(raw_filename):
                raw_filename = fallback_title(source_name, index)
            elif not is_readable_title(raw_filename):
                source_name = str(note.get("__source_name", "来源文档"))
                index = int(note.get("__index", 1))
                raw_filename = fallback_title(source_name, index)
            filename = sanitize_filename(raw_filename)
            content = note.get("content", "")

            target_dir = self.vault_path / category
            target_dir.mkdir(parents=True, exist_ok=True)

            body = clean_existing_header(content)
            header = generate_header(filename, category, body)
            normalized = header + body

            target_path = target_dir / filename
            similar = similarity_target(target_dir, normalized, self.similarity_threshold)
            if similar is not None:
                target_path = similar

            merged_flag = False
            if target_path.exists():
                old = target_path.read_text(encoding="utf-8")
                merged_content, merged_flag = merge_content(old, normalized)
                if not merged_content.strip():
                    dump_failed_payload(self.failed_dir, {
                        "error": "merge_empty_result",
                        "file": str(target_path),
                        "old_preview": old[:300],
                        "new_preview": normalized[:300],
                    })
                    return False, False, None
                target_path.write_text(merged_content, encoding="utf-8")
                print(f"[MERGE] {target_path}")
                return True, merged_flag, str(target_path)

            target_path.write_text(normalized, encoding="utf-8")
            print(f"[SAVE] {target_path}")
            return True, False, str(target_path)
        except Exception as exc:  # noqa: BLE001
            append_log(self.log_dir / "write_error.log", str(exc))
            print(f"[ERROR] 写入失败: {exc}")
            return False, False, None

    def _bridge_export(self, note_path: Path, note: dict) -> None:
        if not self.bridge_export_enabled or not self.bridge_os_root:
            return
        try:
            bucket = self._decide_bridge_bucket(note)
            subfolder = self.bridge_subfolder_map.get(bucket)
            if not subfolder:
                return
            material_root = self.bridge_os_root / self.bridge_material_root
            target_dir = material_root / subfolder
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / note_path.name
            if target.exists():
                stem = target.stem
                suffix = target.suffix
                idx = 1
                while target.exists():
                    target = target_dir / f"{stem}_{idx}{suffix}"
                    idx += 1
            shutil.copy2(note_path, target)
            print(f"[BRIDGE] {note_path.name} -> {target}")
        except Exception as exc:  # noqa: BLE001
            append_log(self.log_dir / "bridge_error.log", f"{note_path}: {exc}")

    def _decide_bridge_bucket(self, note: dict) -> str:
        filename = str(note.get("filename", "")).lower()
        category = str(note.get("category", ""))
        content = str(note.get("content", ""))

        if "洞察" in category or "insight" in filename or "quote" in filename:
            return "quote"

        if any(k in filename for k in ["sop", "prompt", "模板", "结构", "framework"]):
            return "structure"

        if any(k in filename for k in ["theory", "logic", "decision", "原则", "模型"]):
            return "concept"

        if "###" in content and ("步骤" in content or "模型" in content):
            return "structure"

        return "concept"


def summary_to_text(summary: dict) -> str:
    return json.dumps(summary, ensure_ascii=False)
