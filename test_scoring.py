from domain.ats_scorer import ATSScorer
from domain.bullet_point_auditor import BulletPointAuditor

# --------------------------------------------------------------------------
# ATSScorer: verify the overlap math
# --------------------------------------------------------------------------

def test_overlap_half_of_keywords_match():
    # Resume contains "python" and "fastapi" but not "docker" or "kubernetes".
    # 2 matched / 4 unique required keywords = 50.0%.
    scorer = ATSScorer()
    resume = "Experienced developer skilled in Python and FastAPI."
    job_keywords = ["python", "fastapi", "docker", "kubernetes"]
    assert scorer.calculate_overlap(resume, job_keywords) == 50.0

def test_overlap_all_keywords_match():
    scorer = ATSScorer()
    resume = "I know Python, SQL, and React."
    job_keywords = ["python", "sql", "react"]
    assert scorer.calculate_overlap(resume, job_keywords) == 100.0

def test_overlap_no_keywords_match():
    scorer = ATSScorer()
    resume = "I enjoy painting and hiking."
    job_keywords = ["python", "sql"]
    assert scorer.calculate_overlap(resume, job_keywords) == 0.0

def test_overlap_is_case_insensitive():
    scorer = ATSScorer()
    resume = "Built services with PYTHON."
    job_keywords = ["Python"]
    assert scorer.calculate_overlap(resume, job_keywords) == 100.0

def test_overlap_deduplicates_job_keywords():
    # "python" appears three times in the input but must count as ONE keyword.
    # Resume matches python but not sql: 1 matched / 2 unique = 50.0%.
    scorer = ATSScorer()
    resume = "Python developer."
    job_keywords = ["python", "python", "python", "sql"]
    assert scorer.calculate_overlap(resume, job_keywords) == 50.0

def test_overlap_empty_job_keywords_returns_zero():
    # No required keywords means nothing to match against: avoid divide-by-zero.
    scorer = ATSScorer()
    assert scorer.calculate_overlap("any resume text", []) == 0.0

# --------------------------------------------------------------------------
# BulletPointAuditor: verify number detection
# --------------------------------------------------------------------------

def test_flags_only_unquantified_bullets():
    auditor = BulletPointAuditor()
    bullets = [
        "Reduced page load time by 40%",        # quantified -> keep
        "Led the backend team",                 # no number  -> flagged
        "Managed 12 microservices",             # quantified -> keep
        "Improved overall system reliability",  # no number  -> flagged
    ]
    flagged = auditor.flag_unquantified(bullets)
    assert flagged == ["Led the backend team", "Improved overall system reliability"]

def test_all_bullets_quantified_returns_empty():
    auditor = BulletPointAuditor()
    bullets = ["Cut costs by $5000", "Shipped 3 features"]
    assert auditor.flag_unquantified(bullets) == []

def test_empty_bullet_list_returns_empty():
    auditor = BulletPointAuditor()
    assert auditor.flag_unquantified([]) == []
