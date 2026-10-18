from dataclasses import dataclass, field

import pymupdf


@dataclass
class DocumentText:
    text: str
    page_count: int
    char_count: int
    warnings: list[dict[str, str]] = field(default_factory=list)


MAX_DOCUMENT_CHARACTERS = 120_000


def extract_text(pdf_bytes: bytes, supplier_name: str = "") -> DocumentText:
    if not pdf_bytes:
        raise ValueError("The uploaded PDF is empty.")
    try:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            pages = [page.get_text("text") for page in document]
            text = "\n\n".join(pages).strip()
            page_count = document.page_count
    except Exception as error:
        raise ValueError("The uploaded file could not be read as a PDF.") from error

    warnings = []
    if not text:
        raise ValueError("No selectable text was found; scanned/image-only PDFs are not supported.")
    if len(text) > MAX_DOCUMENT_CHARACTERS:
        text = text[:MAX_DOCUMENT_CHARACTERS]
        warnings.append({"supplier": supplier_name, "criterion_id": None, "code": "DOCUMENT_TRUNCATED",
                         "message": f"Document text exceeded {MAX_DOCUMENT_CHARACTERS:,} characters and was truncated."})
    return DocumentText(text, page_count, len(text), warnings)