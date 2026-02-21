import datetime
import difflib
import json
import os
import re
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def read_file_content(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext in IMAGE_EXTENSIONS:
        return read_image_ocr(file_path)
    if ext == ".docx":
        return read_docx_content(file_path)
    if ext == ".doc":
        raise RuntimeError("Legacy .doc is not supported directly. Convert to .docx and retry.")
    if ext == ".pdf":
        try:
            import PyPDF2  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("PyPDF2 is required for PDF input. Install dependencies first.") from exc
        reader = PyPDF2.PdfReader(str(file_path))
        chunks = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                chunks.append(text)
        return "\n".join(chunks)

    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return file_path.read_text(encoding="gbk", errors="ignore")


def read_image_ocr(file_path: Path) -> str:
    """Run OCR on image files via PaddleOCR."""
    try:
        from paddleocr import PaddleOCR  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "PaddleOCR is required for image OCR. Use Python 3.10 venv with paddleocr installed."
        ) from exc

    cache_home = os.getenv("PADDLE_PDX_CACHE_HOME")
    if not cache_home:
        os.environ["PADDLE_PDX_CACHE_HOME"] = "D:/pdxcache"
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "true")

    ocr = PaddleOCR(
        lang="ch",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    result = ocr.predict(str(file_path))
    if not result:
        return ""
    texts = result[0].get("rec_texts", []) if isinstance(result[0], dict) else []
    return "\n".join([t for t in texts if isinstance(t, str) and t.strip()])


def read_docx_content(file_path: Path) -> str:
    """Extract text from .docx without extra dependencies."""
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            xml_bytes = zf.read("word/document.xml")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Failed to read .docx file: {file_path.name}") from exc

    try:
        root = ElementTree.fromstring(xml_bytes)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Invalid .docx XML content: {file_path.name}") from exc

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    lines = []
    for para in root.findall(".//w:p", ns):
        texts = [node.text for node in para.findall(".//w:t", ns) if node.text]
        line = "".join(texts).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def sanitize_filename(name: str) -> str:
    cleaned = name.replace("/", "_").replace("\\", "_").replace(":", "_")
    cleaned = cleaned.replace("*", "_").replace("?", "_").replace('"', "_")
    cleaned = cleaned.replace("<", "_").replace(">", "_").replace("|", "_")
    cleaned = cleaned.strip().strip(".")
    if not cleaned:
        cleaned = "待整理"
    if not cleaned.endswith(".md"):
        cleaned += ".md"
    return cleaned


def is_readable_title(text: str) -> bool:
    if not text:
        return False
    if "�" in text:
        return False
    core = text.replace(".md", "")
    if len(core.strip()) < 2:
        return False
    readable_chars = sum(1 for ch in core if re.match(r"[A-Za-z0-9\u4e00-\u9fff]", ch))
    ratio = readable_chars / max(len(core), 1)
    return ratio >= 0.4


def has_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text or ""))


def fallback_title(source_name: str, index: int) -> str:
    stem = Path(source_name).stem
    stem = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff_-]", "_", stem)
    stem = stem.strip("_")
    if not stem:
        stem = "来源文档"
    ts = datetime.datetime.now().strftime("%m%d_%H%M%S")
    return f"{stem}_条目{index:02d}_{ts}.md"


def clean_existing_header(content: str) -> str:
    pattern_yaml = r"^\s*---\s*\n(.*?)\n\s*---\s*\n"
    match_yaml = re.match(pattern_yaml, content, re.DOTALL)
    body = content[match_yaml.end():].strip() if match_yaml else content

    lines = body.split("\n")
    cleaned_lines = []
    skipping_callout = False
    for i, line in enumerate(lines):
        if i < 5 and line.strip().startswith("# "):
            continue
        if "> [!abstract] 元数据头" in line:
            skipping_callout = True
            continue
        if skipping_callout:
            if line.strip().startswith(">") or not line.strip():
                continue
            skipping_callout = False
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def determine_type_code(filename: str, content: str) -> str:
    fn = filename.upper()
    ct = content.upper()
    if "SOP" in fn or "步骤" in fn:
        return "SOP"
    if "价格" in fn:
        return "PRICE"
    if "用户" in fn:
        return "USER"
    if "拉新" in ct:
        return "PULL"
    if "转化" in ct:
        return "CONV"
    if "信任" in ct:
        return "TRUST"
    if "原理" in fn or "理论" in fn:
        return "THEORY"
    if "决策" in fn or "DECISION" in fn:
        return "DECISION"
    if "画像" in fn or "IDENTITY" in fn:
        return "IDENTITY"
    return "GEN"


def determine_role(category: str) -> str:
    prefix = category.split("_")[0]
    if prefix == "01":
        return "心理教练"
    if prefix in {"02", "03"}:
        return "内容教练"
    if prefix in {"04", "05", "06"}:
        return "商业教练"
    return "全员"


def determine_weight(filename: str, content: str, category: str) -> str:
    prefix = category.split("_")[0]
    fn = filename.upper()
    if prefix in {"01", "06", "07"}:
        return "Critical"
    if prefix in {"02", "04"}:
        return "High"
    if "碎碎念" in fn or "感悟" in fn or "随笔" in fn:
        return "Low"
    return "Medium"


def generate_doc_id(category: str, type_code: str) -> str:
    room_num = category.split("_")[0] if "_" in category else "00"
    ts = datetime.datetime.now().strftime("%H%M%S")
    return f"DOC-{room_num}-{type_code}-{ts}"


def generate_header(filename: str, category: str, content: str) -> str:
    today = datetime.date.today().isoformat()
    room_num = category.split("_")[0] if "_" in category else "00"
    type_code = determine_type_code(filename, content)
    doc_id = generate_doc_id(category, type_code)
    role = determine_role(category)
    weight = determine_weight(filename, content, category)
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    body_lines = [l for l in lines if not l.startswith("#")]
    conclusion = (body_lines[0][:50] + "...") if body_lines else "待人工补充"

    return (
        "---\n"
        f"aliases: []\n"
        f"tags: [IP_Brain/{room_num}, {type_code}]\n"
        f"created: {today}\n"
        "status: Active\n"
        "---\n\n"
        f"# {Path(filename).stem}\n\n"
        "> [!abstract] 元数据头 (AI Read Only)\n"
        f"> **【文档ID】** {doc_id}\n"
        f"> **【文档标题】** {filename}\n"
        f"> **【所属模块】** {category}\n"
        f"> **【适用角色】** {role}\n"
        f"> **【核心结论】** {conclusion}\n"
        "> **【调用触发】** 自动生成\n"
        f"> **【冲突权重】** {weight}\n\n"
    )


def similarity_target(target_dir: Path, candidate: str, threshold: float) -> Path | None:
    best_file = None
    highest = 0.0
    for existing in target_dir.glob("*.md"):
        try:
            old = existing.read_text(encoding="utf-8")
        except Exception:
            continue
        ratio = difflib.SequenceMatcher(None, candidate, old).ratio()
        if ratio > highest:
            highest = ratio
            best_file = existing
    if best_file and highest > threshold:
        return best_file
    return None


def archive_file(src: Path, archive_dir: Path) -> Path:
    archive_dir.mkdir(parents=True, exist_ok=True)
    target = archive_dir / src.name
    if target.exists():
        target = archive_dir / f"{src.stem}_{int(datetime.datetime.now().timestamp())}{src.suffix}"
    shutil.move(str(src), str(target))
    return target


def append_log(log_file: Path, message: str) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"{ts} {message}\n")


def dump_failed_payload(failed_dir: Path, payload: dict) -> Path:
    failed_dir.mkdir(parents=True, exist_ok=True)
    name = f"failed_{int(datetime.datetime.now().timestamp() * 1000)}.json"
    p = failed_dir / name
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p
