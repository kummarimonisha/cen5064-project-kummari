import io

import docx
import PyPDF2


class DocumentParseError(Exception):
    """Raised when a document cannot be read or contains no extractable text.

    Lives in the Data tier so the Service tier can translate it into an
    appropriate response without knowing which parsing library failed.
    """


def extract_text_from_file(filename: str, content: bytes) -> str:
    """Extract raw text locally from a PDF or DOCX file.

    No external APIs are used — parsing happens entirely in-process.

    Raises:
        DocumentParseError: if the file is unsupported, corrupt, or has no
            extractable text.
    """
    name = filename.lower()

    if name.endswith(".pdf"):
        extracted_text = _extract_pdf(content)
    elif name.endswith(".docx"):
        extracted_text = _extract_docx(content)
    else:
        raise DocumentParseError("Unsupported file type. Only PDF or DOCX are allowed.")

    extracted_text = extracted_text.strip()
    if not extracted_text:
        raise DocumentParseError("No readable text found in the document.")

    return extracted_text


def _extract_pdf(content: bytes) -> str:
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        pages = []
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                pages.append(page_text)
        return "\n".join(pages)
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError("Could not read the PDF file; it may be corrupt.") from exc


def _extract_docx(content: bytes) -> str:
    try:
        doc = docx.Document(io.BytesIO(content))
        return "\n".join(para.text for para in doc.paragraphs)
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError("Could not read the DOCX file; it may be corrupt.") from exc
