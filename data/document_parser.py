import io
from abc import ABC, abstractmethod
from typing import ClassVar

import docx
import PyPDF2

# A newline built with chr(10) so copy-pasting this file can never turn a
# backslash-n into a real line break inside a string.
NL = chr(10)

class DocumentParseError(Exception):
    """Raised when a document cannot be read or contains no extractable text.

    Lives in the Data tier so the Service tier can react to one known error
    type without knowing which parsing library failed.
    """

class ResumeParser(ABC):
    """Abstract product: something that turns file bytes into text.

    Each concrete parser (PDF, DOCX) implements extract(). New formats are
    added by writing a NEW subclass + registering it in ParserFactory -- the
    existing parsers are never edited. That is the Open/Closed Principle, and
    the factory below is the Factory Method pattern that chooses which one to
    build.
    """

    @abstractmethod
    def extract(self, content: bytes) -> str:
        """Return the raw text contained in the given file bytes."""
        raise NotImplementedError

class PdfParser(ResumeParser):
    """Concrete parser for PDF files."""

    def extract(self, content: bytes) -> str:
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            pages = []
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:  # scanned-image pages can yield no text
                    pages.append(page_text)
            return NL.join(pages)
        except DocumentParseError:
            raise
        except Exception as exc:
            raise DocumentParseError("Could not read the PDF file; it may be corrupt.") from exc

class DocxParser(ResumeParser):
    """Concrete parser for DOCX files."""

    def extract(self, content: bytes) -> str:
        try:
            doc = docx.Document(io.BytesIO(content))
            return NL.join(para.text for para in doc.paragraphs)
        except DocumentParseError:
            raise
        except Exception as exc:
            raise DocumentParseError("Could not read the DOCX file; it may be corrupt.") from exc

class ParserFactory:
    """Factory Method: pick the right ResumeParser for a filename.

    Adding a new format (e.g. .txt) means adding one entry here and one new
    parser class -- no existing code changes.
    """

    _PARSERS: ClassVar[dict[str, type[ResumeParser]]] = {
        ".pdf": PdfParser,
        ".docx": DocxParser,
    }

    @classmethod
    def get_parser(cls, filename: str) -> ResumeParser:
        name = filename.lower()
        for extension, parser_cls in cls._PARSERS.items():
            if name.endswith(extension):
                return parser_cls()
        raise DocumentParseError("Unsupported file type. Only PDF or DOCX are allowed.")

def extract_text_from_file(filename: str, content: bytes) -> str:
    """Extract raw text locally from a PDF or DOCX file.

    Thin Data-tier entry point: the factory chooses the parser, the parser does
    the work. No external APIs are used.

    Raises:
        DocumentParseError: if the file is unsupported, corrupt, or has no
            extractable text.
    """
    parser = ParserFactory.get_parser(filename)
    extracted_text = parser.extract(content).strip()
    if not extracted_text:
        raise DocumentParseError("No readable text found in the document.")
    return extracted_text
