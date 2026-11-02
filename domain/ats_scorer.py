import re

# Very common words that carry no signal as "keywords". Filtered out so the
# score reflects real skills/terms, not filler like "the" or "and".
_STOPWORDS = {
    "the", "and", "for", "with", "you", "our", "are", "that", "this", "will",
    "have", "has", "a", "an", "to", "of", "in", "on", "or", "is", "be", "as",
    "we", "at", "by", "it", "your",
}

# A "word" is a run of letters/digits/+/#, so terms like "c++" and "c#" survive.
_WORD_PATTERN = re.compile(r"[a-zA-Z0-9+#]+")

class ATSScorer:
    """Domain tier: deterministic ATS keyword-overlap scoring.

    This is a pure business rule. It knows nothing about FastAPI, uploaded
    files, or the database. It takes plain text / plain Python data and returns
    a calculated number.

    The score answers one question: "What percentage of the job's required
    keywords does the resume actually contain?"
    """

    def extract_keywords(self, job_text: str) -> list[str]:
        """Turn raw job-description text into a list of candidate keywords.

        Lower-cases the text, splits it into words, drops common stopwords and
        single-character tokens. Deterministic: the same text always yields the
        same keywords.
        """
        words = _WORD_PATTERN.findall(job_text.lower())
        return [w for w in words if len(w) > 1 and w not in _STOPWORDS]

    def score_text(self, resume_text: str, job_text: str) -> float:
        """Score a resume against raw job-description TEXT.

        This is the end-to-end entry point the Service tier uses: it extracts
        the job's keywords from the text, then measures overlap. Given a resume
        and a job description, it returns the match percentage.
        """
        job_keywords = self.extract_keywords(job_text)
        return self.calculate_overlap(resume_text, job_keywords)

    def calculate_overlap(self, resume_text: str, job_keywords: list[str]) -> float:
        """Return the keyword overlap as a percentage (0.0 - 100.0).

        Formula:
            (matched unique job keywords / total unique job keywords) * 100

        Args:
            resume_text: the full parsed resume text.
            job_keywords: the keywords extracted from the job description.
                Duplicates are allowed in the input; they are de-duplicated
                here so a single keyword can never be counted twice.

        Returns:
            The overlap percentage, rounded to two decimal places. Returns 0.0
            when the job has no keywords (nothing to match against).
        """
        # De-duplicate the job keywords so each required keyword counts once.
        # Lower-casing makes the match case-insensitive ("Python" == "python").
        unique_job_keywords = {keyword.lower() for keyword in job_keywords}

        # Guard against division by zero: no required keywords means no score.
        if not unique_job_keywords:
            return 0.0

        # Lower-case the resume text once so matching is case-insensitive.
        resume_lower = resume_text.lower()

        # Count how many of the required keywords appear in the resume.
        matched = {
            keyword for keyword in unique_job_keywords if keyword in resume_lower
        }

        overlap = (len(matched) / len(unique_job_keywords)) * 100
        return round(overlap, 2)
