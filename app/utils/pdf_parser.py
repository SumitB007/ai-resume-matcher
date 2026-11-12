"""PDF text extraction using pdfplumber."""

import io

import pdfplumber


def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract all text from a PDF file.

    Args:
        file_content: Raw bytes of the PDF file.

    Returns:
        Extracted text as a single string, with pages separated by newlines.
    """
    text_parts: list[str] = []

    with pdfplumber.open(io.BytesIO(file_content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    return "\n\n".join(text_parts)
