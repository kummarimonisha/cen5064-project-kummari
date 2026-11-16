import re

# Curated dictionary of real ATS keywords: technologies, languages, tools, and
# professional practices an applicant-tracking system actually looks for. The
# scorer only considers these -- not every word in the posting -- so the score
# reflects meaningful skills (tech stack, methodologies), like a real ATS.
#
# Multi-word phrases ("data structures", "machine learning") are supported and
# counted as a single keyword. Add new terms here as the domain grows; this is
# the one place keyword knowledge lives.
_KNOWN_SKILLS = {
    # languages
    "python", "java", "javascript", "typescript", "c++", "c#", "c", "go",
    "golang", "ruby", "rust", "kotlin", "swift", "scala", "php", "r", "ocaml",
    "sql", "html", "css", "bash", "matlab",
    # frameworks / libraries
    "react", "angular", "vue", "next.js", "node.js", "node", "express",
    "django", "flask", "fastapi", "spring", "spring boot", ".net", "rails",
    "ruby on rails", "jquery", "pandas", "numpy", "tensorflow", "pytorch",
    "scikit-learn",
    # data / databases
    "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis",
    "data structures", "data modeling", "data analysis", "databases",
    "etl", "data pipelines", "big data", "spark", "hadoop",
    # cloud / devops / tools
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "terraform",
    "git", "github", "gitlab", "ci/cd", "jenkins", "linux", "rest", "rest api",
    "graphql", "microservices", "api", "apis", "firebase",
    # practices / methodologies / concepts
    "agile", "scrum", "kanban", "tdd", "test driven development", "unit testing",
    "oop", "object oriented", "machine learning", "deep learning",
    "distributed systems", "algorithms", "version control", "code review",
    "design patterns",
    # domains
    "gaming", "cybersecurity", "security", "frontend", "backend", "full stack",
    "mobile", "android", "ios",
}

def _word_regex(skill: str) -> re.Pattern:
    """Compile a whole-word, case-insensitive regex for a skill phrase.

    Whole-word matching means "java" does NOT match inside "javascript", and
    multi-word phrases match as a unit. Special characters in a skill (like the
    + in c++) are escaped. The boundaries are letters/digits/+/# only -- NOT
    the period -- so a skill at the end of a sentence ("Python.") still matches
    while "javascript" still does not count as "java".
    """
    escaped = re.escape(skill)
    return re.compile(rf"(?<![a-zA-Z0-9+#]){escaped}(?![a-zA-Z0-9+#])", re.IGNORECASE)

# Pre-compile every skill's matcher once (keyword -> compiled regex).
_SKILL_REGEX = {skill: _word_regex(skill) for skill in _KNOWN_SKILLS}

class ATSScorer:
    """Domain tier: deterministic ATS keyword scoring against a curated skill set.

    A pure business rule: no FastAPI, no files, no network. It identifies which
    KNOWN skills a job description asks for, then checks which of those appear
    in the resume, and reports a match percentage plus the matched/missing lists.
    """

    def extract_keywords(self, job_text: str) -> list[str]:
        """Return the known skills that appear in the job-description text.

        Only curated skills are considered, so the result is the real "required
        keywords" (tech stack, practices) -- not every word in the posting.
        Sorted for a stable, readable order.
        """
        return sorted(
            skill for skill, pattern in _SKILL_REGEX.items() if pattern.search(job_text)
        )

    def _skills_in(self, text: str) -> set:
        """Return the set of known skills present in the given text."""
        return {skill for skill, pattern in _SKILL_REGEX.items() if pattern.search(text)}

    def score_report(self, resume_text: str, job_text: str) -> dict:
        """Full report: score plus which required skills matched or are missing.

        required = known skills mentioned in the job description
        matched  = required skills that also appear in the resume
        missing  = required skills absent from the resume
        score    = matched / required * 100
        """
        required = set(self.extract_keywords(job_text))
        if not required:
            return {"score": 0.0, "matched_keywords": [], "missing_keywords": []}

        resume_skills = self._skills_in(resume_text)
        matched = sorted(required & resume_skills)
        missing = sorted(required - resume_skills)
        score = round((len(matched) / len(required)) * 100, 2)

        return {
            "score": score,
            "matched_keywords": matched,
            "missing_keywords": missing,
        }

    def score_text(self, resume_text: str, job_text: str) -> float:
        """Convenience entry point: return just the match percentage."""
        return self.score_report(resume_text, job_text)["score"]

    def calculate_overlap(self, resume_text: str, job_keywords: list[str]) -> float:
        """Return the overlap percentage for an explicit list of keywords.

        Kept for callers that already have a keyword list. De-duplicates the
        keywords and uses whole-word matching against the resume.
        """
        unique = {k.lower() for k in job_keywords}
        if not unique:
            return 0.0
        matched = sum(1 for k in unique if _word_regex(k).search(resume_text))
        return round((matched / len(unique)) * 100, 2)
