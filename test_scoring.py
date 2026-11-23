from domain.ats_scorer import ATSScorer
from domain.bullet_point_auditor import BulletPointAuditor

# --------------------------------------------------------------------------
# ATSScorer: curated-skill keyword matching
# --------------------------------------------------------------------------

def test_extract_keywords_only_returns_known_skills():
    # Only real skills from the job text are returned -- not filler words.
    scorer = ATSScorer()
    job = "We want Python and SQL experience. You will collaborate with the team."
    keywords = scorer.extract_keywords(job)
    assert "python" in keywords
    assert "sql" in keywords
    # filler words are NOT keywords
    assert "collaborate" not in keywords
    assert "team" not in keywords
    assert "experience" not in keywords

def test_matching_is_whole_word():
    # "java" must NOT match inside "javascript".
    scorer = ATSScorer()
    report = scorer.score_report("I only know javascript.", "Need Java")
    assert report["matched_keywords"] == []
    assert report["missing_keywords"] == ["java"]
    assert report["score"] == 0.0

def test_multi_word_phrase_is_one_keyword():
    scorer = ATSScorer()
    job = "Strong data structures and algorithms."
    keywords = scorer.extract_keywords(job)
    assert "data structures" in keywords
    assert "algorithms" in keywords

def test_score_report_matched_and_missing():
    # Resume has python + sql; job requires python, sql, docker, aws.
    # 2 matched / 4 required = 50%.
    scorer = ATSScorer()
    resume = "Skilled in Python and SQL."
    job = "Need Python, SQL, Docker and AWS."
    report = scorer.score_report(resume, job)
    assert report["score"] == 50.0
    assert report["matched_keywords"] == ["python", "sql"]
    assert report["missing_keywords"] == ["aws", "docker"]

def test_score_report_all_matched():
    scorer = ATSScorer()
    report = scorer.score_report("Python, SQL, React.", "Need Python SQL React")
    assert report["score"] == 100.0
    assert report["missing_keywords"] == []

def test_score_report_is_case_insensitive():
    scorer = ATSScorer()
    report = scorer.score_report("Built services with PYTHON.", "Need python")
    assert report["score"] == 100.0

def test_score_report_no_known_skills_in_job_is_zero():
    # Job mentions no known skills at all -> nothing to score against.
    scorer = ATSScorer()
    report = scorer.score_report("Python developer.", "We want a friendly person.")
    assert report["score"] == 0.0
    assert report["matched_keywords"] == []
    assert report["missing_keywords"] == []

def test_score_text_convenience():
    scorer = ATSScorer()
    assert scorer.score_text("Python and SQL", "Need Python SQL Docker AWS") == 50.0

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
