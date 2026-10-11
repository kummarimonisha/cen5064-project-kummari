import io

import docx
import PyPDF2

# Custom error type for the Data tier. Raised when a document cannot be read
# or contains no extractable text. Keeping it here (rather than letting a raw
# PyPDF2/docx exception escape) lets the Service tier react to one known error
# without knowing which parsing library was used underneath.
class DocumentParseError(Exception):
    pass

def extract_text_from_file(filename: str, content: bytes) -> str:
    """Extract raw text locally from a PDF or DOCX file.

    No external APIs are used; parsing happens entirely in-process.

    Raises:
        DocumentParseError: if the file is unsupported, corrupt, or has no
            extractable text.
    """
    # Lower-case the name so ".PDF" / ".Docx" are handled the same way.
    name = filename.lower()

    # Pick the right extractor based on the file extension.
    if name.endswith(".pdf"):
        extracted_text = _extract_pdf(content)
    elif name.endswith(".docx"):
        extracted_text = _extract_docx(content)
    else:
        raise DocumentParseError("Unsupported file type. Only PDF or DOCX are allowed.")

    # A valid-but-empty document (e.g. a blank page) is not useful for analysis,
    # so treat "no text" as an error the caller can report cleanly.
    extracted_text = extracted_text.strip()
    if not extracted_text:
        raise DocumentParseError("No readable text found in the document.")

    return extracted_text

def _extract_pdf(content: bytes) -> str:
    """Read every page of a PDF (given as raw bytes) and join the text."""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        pages = []
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:  # some pages (e.g. scanned images) yield no text
                pages.append(page_text)
        return "
".join(pages)
    except DocumentParseError:
        # Already our own error type; let it propagate unchanged.
        raise
    except Exception as exc:
        # Any library-level failure (corrupt/unreadable file) becomes our error.
        raise DocumentParseError("Could not read the PDF file; it may be corrupt.") from exc

def _extract_docx(content: bytes) -> str:
    """Read every paragraph of a DOCX (given as raw bytes) and join the text."""
    try:
        doc = docx.Document(io.BytesIO(content))
        return "
".join(para.text for para in doc.paragraphs)
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError("Could not read the DOCX file; it may be corrupt.") from exc
