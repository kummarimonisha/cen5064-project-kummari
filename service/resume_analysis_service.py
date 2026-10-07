from data.document_parser import DocumentParseError, extract_text_from_file


class ResumeAnalysisService:
    """Service tier: orchestrates resume analysis.

    For Issue #1 it coordinates one step — asking the Data tier to extract
    text from the uploaded document. Later issues (ATS scoring, AI bullet
    refinement) extend this orchestration. The Presentation tier calls this
    service and never touches the Data tier directly.
    """

    def extract_resume_text(self, filename: str, content: bytes) -> str:
        """Extract raw text from an uploaded resume document.

        Raises:
            DocumentParseError: if the document is unsupported, corrupt, or
                has no extractable text. The Presentation tier is responsible
                for turning this into an HTTP response.
        """
        return extract_text_from_file(filename, content)


__all__ = ["DocumentParseError", "ResumeAnalysisService"]
