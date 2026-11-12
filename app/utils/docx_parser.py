"""DOCX text extraction using python-docx."""

import io

from docx import Document


def extract_text_from_docx(file_content: bytes) -> str:
    """Extract all text from a DOCX file.

    Args:
        file_content: Raw bytes of the DOCX file.

    Returns:
        Extracted text as a single string, with paragraphs separated by newlines.
    """
    doc = Document(io.BytesIO(file_content))
    text_parts: list[str] = []

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text:
            text_parts.append(text)

    # Also extract text from tables
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                text_parts.append(row_text)

    return "\n".join(text_parts)
