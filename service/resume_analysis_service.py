from data.document_parser import DocumentParseError, extract_text_from_file
from domain.ats_scorer import ATSScorer
from domain.bullet_point_auditor import BulletPointAuditor


class ResumeAnalysisService:
    """Service tier: orchestrates resume analysis.

    It coordinates the lower tiers for one request:
      1. ask the Data tier to extract text from the uploaded document,
      2. ask the Domain tier (ATSScorer) to score that text against the job and
         report matched / missing keywords,
      3. ask the Domain auditor which bullets are unquantified and hand those to
         the Data tier AI client for rewriting.
    The Presentation tier calls this service and never touches the Data or
    Domain tiers directly. The service holds no business rules itself -- the
    scoring/auditing math lives in the Domain tier and the AI call lives in the
    Data tier.
    """

    def __init__(self, scorer=None, auditor=None, ai_client=None, repository=None):
        # Dependencies default to real implementations but can be injected,
        # which is what the tests do (fake scorer / auditor / AI client /
        # repository). This is the Dependency Inversion Principle in miniature.
        self._scorer = scorer or ATSScorer()
        self._auditor = auditor or BulletPointAuditor()
        self._ai_client = ai_client
        # The repository persists results. It is optional so the service can be
        # used (and tested) without a database; when present, analyze() saves.
        self._repository = repository

    def extract_resume_text(self, filename: str, content: bytes) -> str:
        """Extract raw text from an uploaded resume document (Issue #1).

        Raises:
            DocumentParseError: if the document is unsupported, corrupt, or has
                no extractable text.
        """
        return extract_text_from_file(filename, content)

    def analyze(self, filename: str, content: bytes, job_text: str) -> dict:
        """Parse the resume and score it, returning the full report (Issue #2/#4).

        Returns the extracted text plus the ATS score and the matched / missing
        keyword lists the UI displays.

        Raises:
            DocumentParseError: if the document cannot be parsed.
        """
        resume_text = extract_text_from_file(filename, content)
        report = self._scorer.score_report(resume_text, job_text)
        result = {
            "extracted_text": resume_text,
            "ats_score": report["score"],
            "matched_keywords": report["matched_keywords"],
            "missing_keywords": report["missing_keywords"],
        }
        # Persist the result (logic -> storage) when a repository is configured.
        if self._repository is not None:
            self._repository.save_analysis(filename, result)
        return result

    def refine_bullets(self, bullets: list[str], job_text: str) -> list[dict]:
        """Rewrite unquantified bullets with the AI client (Issue #3/#4).

        Flow (all tiers, one way down):
          Domain auditor  -> which bullets lack a number
          Domain scorer   -> turn the job text into target keywords
          Data AI client  -> rewrite the flagged bullets for that job

        Returns a list of {"before", "after"} pairs so the UI can show the
        original and the improved version side by side. Returns an empty list
        when no bullet needs refining.

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
        revisions = self._ai_client.generate_revisions(flagged, job_keywords)

        return [
            {"before": original, "after": rewritten}
            for original, rewritten in zip(flagged, revisions)
        ]

__all__ = ["DocumentParseError", "ResumeAnalysisService"]
