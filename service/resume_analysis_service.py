from data.document_parser import DocumentParseError, extract_text_from_file
from domain.ats_scorer import ATSScorer
from domain.bullet_point_auditor import BulletPointAuditor


class ResumeAnalysisService:
    """Service tier: orchestrates resume analysis.

    It coordinates the lower tiers for one request:
      1. ask the Data tier to extract text from the uploaded document,
      2. ask the Domain tier (ATSScorer) to score that text against the job,
      3. (Issue #3) ask the Domain auditor which bullets are unquantified and
         hand those to the Data tier AI client for rewriting.
    The Presentation tier calls this service and never touches the Data or
    Domain tiers directly. The service holds no business rules itself — the
    scoring/auditing math lives in the Domain tier and the AI call lives in the
    Data tier.
    """

    def __init__(
        self,
        scorer: ATSScorer | None = None,
        auditor: BulletPointAuditor | None = None,
        ai_client=None,
    ):
        # Dependencies default to real implementations but can be injected,
        # which is what the tests do (a fake scorer/auditor/AI client). This is
        # the "depend on the abstraction" idea in miniature.
        self._scorer = scorer or ATSScorer()
        self._auditor = auditor or BulletPointAuditor()
        # The AI client is injected only when the feature is used. We do NOT
        # build a default GeminiAIClient here so the service can be constructed
        # (and most of it tested) without any AI key present.
        self._ai_client = ai_client

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

    def refine_bullets(self, bullets: list[str], job_text: str) -> list[str]:
        """Rewrite the unquantified bullets using the AI client (Issue #3).

        Flow (all tiers, one way down):
          Domain auditor  -> which bullets lack a number
          Domain scorer   -> turn the job text into target keywords
          Data AI client  -> rewrite the flagged bullets for that job

        Args:
            bullets: the candidate experience bullet points.
            job_text: the raw job-description text.

        Returns:
            The AI-rewritten versions of the flagged bullets (empty list if no
            bullet needed refining).

        Raises:
            RuntimeError: if no AI client was configured on this service.
        """
        if self._ai_client is None:
            raise RuntimeError(
                "No AI client configured. Construct ResumeAnalysisService with "
                "an ai_client to use refine_bullets()."
            )

        flagged = self._auditor.flag_unquantified(bullets)
        if not flagged:
            return []

        job_keywords = self._scorer.extract_keywords(job_text)
        return self._ai_client.generate_revisions(flagged, job_keywords)

__all__ = ["DocumentParseError", "ResumeAnalysisService"]
