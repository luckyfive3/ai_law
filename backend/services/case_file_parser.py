"""文件解析器 - PDF/DOCX/TXT"""
import os, logging
logger = logging.getLogger(__name__)

def parse_file(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    try:
        if ext == '.txt':
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
        elif ext == '.pdf':
            try:
                from PyPDF2 import PdfReader
                pages = [p.extract_text() or "" for p in PdfReader(file_path).pages]
                text = '\n'.join(pages)
            except ImportError:
                text = f"[PDF文件需安装PyPDF2: {os.path.basename(file_path)}]"
        elif ext in ('.doc', '.docx'):
            try:
                from docx import Document
                text = '\n'.join(p.text for p in Document(file_path).paragraphs if p.text.strip())
            except ImportError:
                text = f"[Word文件需安装python-docx: {os.path.basename(file_path)}]"
        elif ext in ('.png', '.jpg', '.jpeg'):
            text = f"[图片: {os.path.basename(file_path)}，暂不支持OCR]"
        else:
            text = f"[不支持格式: {ext}]"
    except Exception as e:
        logger.error(f"解析失败 {file_path}: {e}")
        text = f"[解析失败: {os.path.basename(file_path)}]"
    if len(text) > 8000:
        text = text[:8000] + "\n...(已截断至8000字)"
    return text
