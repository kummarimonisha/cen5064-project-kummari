from data.document_parser import DocumentParseError, extract_text_from_file
from domain.ats_scorer import ATSScorer


class ResumeAnalysisService:
    """Service tier: orchestrates resume analysis.

    It coordinates the lower tiers for one request:
      1. ask the Data tier to extract text from the uploaded document, then
      2. ask the Domain tier (ATSScorer) to score that text against the job
         description.
    The Presentation tier calls this service and never touches the Data or
    Domain tiers directly. The service contains no business rules itself — the
    scoring math lives in the Domain tier.
    """

    def __init__(self, scorer: ATSScorer | None = None):
        # Default to a real scorer, but allow one to be injected (useful for
        # tests). This is the "depend on the abstraction" idea in miniature.
        self._scorer = scorer or ATSScorer()

    def extract_resume_text(self, filename: str, content: bytes) -> str:
        """Extract raw text from an uploaded resume document (Issue #1).

        Raises:
            DocumentParseError: if the document is unsupported, corrupt, or has
                no extractable text. The Presentation tier turns this into an
                HTTP response.
        """
        return extract_text_from_file(filename, content)

    def analyze(self, filename: str, content: bytes, job_text: str) -> dict:
        """Run one request all the way from upload to a score (Issue #2).

        Parses the uploaded resume, then scores it against the job-description
        text. Returns the extracted text and the ATS match percentage.

        Raises:
            DocumentParseError: if the document cannot be parsed.
        """
        resume_text = extract_text_from_file(filename, content)
        ats_score = self._scorer.score_text(resume_text, job_text)
        return {
            "extracted_text": resume_text,
            "ats_score": ats_score,
        }

__all__ = ["DocumentParseError", "ResumeAnalysisService"]
