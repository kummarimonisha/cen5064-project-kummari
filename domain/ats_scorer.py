class ATSScorer:
    """Domain tier: deterministic ATS keyword-overlap scoring.

    This is a pure business rule. It knows nothing about FastAPI, uploaded
    files, or the database. It takes plain Python data (the parsed resume text
    and a list of job keywords) and returns a calculated number.

    The score answers one question: "What percentage of the job's required
    keywords does the resume actually contain?"
    """

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
