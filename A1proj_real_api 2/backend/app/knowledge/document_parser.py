"""从 PDF / DOCX 维修手册解析并切块为知识条目。"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable

from app.core.config import get_settings

MAIN_HEADING_RE = re.compile(r"^[一二三四五六七八九十]+、")
FAULT_HEADING_RE = re.compile(r"^\d+\.\s*")


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def make_doc_id(source: str, index: int, title: str) -> str:
    base = Path(source).stem
    slug = re.sub(r"[^A-Za-z0-9\u4e00-\u9fff]+", "_", title).strip("_")[:40]
    return f"{base}_{index:04d}_{slug}"[:80]


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) <= chunk_size:
        return [text] if text else []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def infer_tags(title: str, content: str, source: str) -> list[str]:
    text = f"{title} {content} {source}"
    candidates = [
        "屏幕",
        "Face ID",
        "电池",
        "USB-C",
        "充电",
        "摄像头",
        "主板",
        "Wi-Fi",
        "蓝牙",
        "扬声器",
        "听筒",
        "伺服",
        "数控",
        "西门子",
        "三菱",
        "FANUC",
        "SINUMERIK",
        "808D",
        "报警",
        "诊断",
        "参数",
        "主轴",
        "进给",
        "iPhone 17",
        "数控机床",
    ]
    tags = [t for t in candidates if t in text]
    # 从文件名提取设备型号线索
    stem = Path(source).stem
    if stem and stem not in tags:
        tags.append(stem[:30])
    return list(dict.fromkeys(tags))[:12]


def parse_docx(path: Path) -> list[dict]:
    from docx import Document

    doc = Document(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    if not paragraphs:
        return []

    root_title = paragraphs[0]
    docs: list[dict] = []
    current_title: str | None = None
    current_lines: list[str] = []
    section_prefix = ""

    def flush() -> None:
        nonlocal current_title, current_lines
        if current_title and current_lines:
            content = "\n".join(current_lines).strip()
            docs.append(
                {
                    "title": current_title,
                    "content": content,
                    "source": path.name,
                    "tags": infer_tags(current_title, content, path.name),
                }
            )
        current_title = None
        current_lines = []

    for line in paragraphs[1:]:
        if MAIN_HEADING_RE.match(line):
            flush()
            section_prefix = line
            current_title = f"{root_title}｜{line}"
            current_lines = []
            continue
        if section_prefix.startswith("三、") and FAULT_HEADING_RE.match(line):
            flush()
            current_title = f"{root_title}｜{line}"
            current_lines = []
            continue
        if current_title is None:
            current_title = root_title
        current_lines.append(line)
    flush()
    return docs


def _ocr_pdf_pages(path: Path, page_limit: int = 100, start_page: int = 1) -> str:
    """OCR a scanned PDF — convert pages to images then run Tesseract (Chinese)."""
    import logging
    from pdf2image import convert_from_path
    import pytesseract

    logger = logging.getLogger(__name__)
    logger.info("OCR 扫描 PDF: %s (第 %d-%d 页)", path.name, start_page, start_page + page_limit - 1)

    images = convert_from_path(str(path), dpi=150, first_page=start_page, last_page=start_page + page_limit - 1)
    texts: list[str] = []
    for i, img in enumerate(images):
        try:
            t = pytesseract.image_to_string(img, lang="chi_sim", config="--psm 6")
            if t.strip():
                texts.append(t.strip())
        except Exception as exc:
            logger.warning("OCR page %d failed: %s", i + 1, exc)
        if (i + 1) % 10 == 0:
            logger.info("OCR 进度: %d/%d 页", i + 1, min(page_limit, len(images)))
    logger.info("OCR 完成: %d 页提取到文本", len(texts))
    return "\n\n".join(texts)


def parse_pdf(path: Path) -> list[dict]:
    """解析 PDF，扫描版自动 OCR 回退。"""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ImportError("请安装 pypdf：pip install pypdf") from exc

    try:
        reader = PdfReader(str(path))
    except Exception as e:
        # 文件损坏或为空时返回空列表
        import logging
        logging.getLogger(__name__).warning(f"PDF 解析失败: {path.name} — {e}")
        return []
    total_pages = len(reader.pages)
    pages: list[str] = []
    for page in reader.pages:
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        if t.strip():
            pages.append(t.strip())

    full_text = "\n\n".join(pages)

    # 扫描 PDF 检测：每页平均字符 < 100 视为扫描版
    avg_chars = len(full_text.strip()) / max(total_pages, 1)
    if avg_chars < 100:
        import logging
        logger = logging.getLogger(__name__)
        logger.info("检测到扫描版 PDF (%d 页, 总文本 %d 字, 平均 %.0f 字/页)，启用 OCR",
                    total_pages, len(full_text.strip()), avg_chars)
        full_text = _ocr_pdf_pages(path, page_limit=min(total_pages, 80), start_page=20)
    elif not full_text.strip():
        full_text = _ocr_pdf_pages(path, page_limit=min(total_pages, 80), start_page=20)

    if not full_text.strip():
        return []

    settings = get_settings()
    chunks = chunk_text(full_text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    stem = path.stem
    docs: list[dict] = []
    for i, chunk in enumerate(chunks, start=1):
        first_line = chunk.split("\n", 1)[0].strip()[:60] or f"片段 {i}"
        title = f"{stem}｜{first_line}"
        docs.append(
            {
                "title": title,
                "content": chunk,
                "source": path.name,
                "tags": infer_tags(title, chunk, path.name),
            }
        )
    return docs


def parse_manual_file(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return parse_docx(path)
    if suffix == ".pdf":
        return parse_pdf(path)
    if suffix in (".xls", ".xlsx"):
        return parse_xls(path)
    return []


def parse_xls(path: Path) -> list[dict]:
    """解析 XLS/XLSX 报警代码表，每行一条知识条目。"""
    try:
        import xlrd
    except ImportError as exc:
        raise ImportError("请安装 xlrd：pip install xlrd") from exc

    wb = xlrd.open_workbook(str(path))
    sh = wb.sheet_by_index(0)

    if sh.nrows < 2:
        return []

    # 首行是表头：报警代码 | 名称 | 解析 | 解决方法 | 内部故障码 | 故障类型
    docs: list[dict] = []
    stem = path.stem

    for r in range(1, sh.nrows):
        code = str(sh.cell_value(r, 0)).strip()
        name = str(sh.cell_value(r, 1)).strip()
        analysis = str(sh.cell_value(r, 2)).strip()
        solution = str(sh.cell_value(r, 3)).strip()

        if not code and not name:
            continue

        code_clean = code.replace(".0", "") if code.endswith(".0") else code
        title = f"报警 {code_clean} | {name}" if name else f"报警 {code_clean}"
        content_parts = [f"报警代码：{code_clean}"]
        if name:
            content_parts.append(f"名称：{name}")
        if analysis:
            content_parts.append(f"解析：{analysis}")
        if solution:
            content_parts.append(f"解决方法：{solution}")

        content = "\n".join(content_parts)

        docs.append({
            "title": title,
            "content": content,
            "source": path.name,
            "tags": ["报警", "故障代码", "诊断"] + ([stem[:20]] if stem else []),
        })

    return docs


def assign_ids(raw_docs: Iterable[dict], source: str) -> list[dict]:
    out: list[dict] = []
    for i, doc in enumerate(raw_docs, start=1):
        item = dict(doc)
        item["id"] = make_doc_id(source, i, doc.get("title", "chunk"))
        item.setdefault("source", source)
        item.setdefault("tags", [])
        item["doc_type"] = "manual"
        item["status"] = "approved"
        out.append(item)
    return out
