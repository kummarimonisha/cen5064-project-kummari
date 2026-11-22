"""Generate the final PowerPoint for the Resume Optimizer project.

Run once:  python scripts/make_deck.py
Produces:  CEN5064_Final_Presentation.pptx  in the repo root.

This is a build script, not part of the running app.
"""

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

# ---- palette (pink / aqua ocean) ----
AQUA = RGBColor(0x2E, 0x9F, 0xA2)
AQUA_DARK = RGBColor(0x1F, 0x7E, 0x81)
PINK = RGBColor(0xD8, 0x6A, 0xA0)
INK = RGBColor(0x26, 0x34, 0x3B)
MUTED = RGBColor(0x6D, 0x7C, 0x83)
BG = RGBColor(0xF2, 0xFB, 0xFB)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

W = prs.slide_width
H = prs.slide_height


def add_slide(bg=BG):
    slide = prs.slides.add_slide(BLANK)
    rect = slide.shapes.add_shape(1, 0, 0, W, H)  # 1 = rectangle
    rect.fill.solid()
    rect.fill.fore_color.rgb = bg
    rect.line.fill.background()
    rect.shadow.inherit = False
    slide.shapes._spTree.remove(rect._element)
    slide.shapes._spTree.insert(2, rect._element)
    return slide


def tbox(slide, left, top, width, height):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    return tf


def set_text(frame, text, size, color=INK, bold=False, align=PP_ALIGN.LEFT, first=True):
    p = frame.paragraphs[0] if first else frame.add_paragraph()
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = "Segoe UI"
    return p


def bullets(frame, items, size=18, color=INK):
    for i, (txt, lvl) in enumerate(items):
        p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        p.level = lvl
        run = p.add_run()
        run.text = ("• " if lvl == 0 else "– ") + txt
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.name = "Segoe UI"
        p.space_after = Pt(6)


def title_bar(slide, text):
    bar = slide.shapes.add_shape(1, 0, 0, W, Inches(1.1))
    bar.fill.solid()
    bar.fill.fore_color.rgb = AQUA_DARK
    bar.line.fill.background()
    bar.shadow.inherit = False
    tf = bar.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.5)
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = text
    r.font.size = Pt(28)
    r.font.bold = True
    r.font.color.rgb = WHITE
    r.font.name = "Segoe UI"


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


# ---------------------------------------------------------------- Slide 1 — Title
s = add_slide(AQUA_DARK)
tf = tbox(s, Inches(1), Inches(2.4), Inches(11.3), Inches(2))
set_text(tf, "AI Resume Optimizer & ATS Matcher", 44, WHITE, bold=True, align=PP_ALIGN.CENTER)
set_text(tf, "A full-stack app that scores a resume against a job and rewrites weak bullets with AI",
         20, RGBColor(0xD9, 0xF3, 0xF3), align=PP_ALIGN.CENTER, first=False)
tf2 = tbox(s, Inches(1), Inches(5.6), Inches(11.3), Inches(1))
set_text(tf2, "Monisha Kummari  ·  CEN 5064 Software Design  ·  Fall 2026",
         16, RGBColor(0xBF, 0xE8, 0xE8), align=PP_ALIGN.CENTER)
notes(s, "Hi, I'm Monisha. This is my AI Resume Optimizer and ATS Matcher for CEN 5064. "
         "It's a full-stack app: a candidate uploads a resume, pastes a job description, gets an "
         "ATS keyword match score, and can rewrite weak bullet points with AI.")

# ---------------------------------------------------------------- Slide 2 — Problem
s = add_slide()
title_bar(s, "The problem")
tf = tbox(s, Inches(0.7), Inches(1.5), Inches(11.9), Inches(5))
bullets(tf, [
    ("Most resumes are first read by an Applicant Tracking System (ATS), not a human.", 0),
    ("If a resume is missing the job's key skills/keywords, it gets filtered out before anyone sees it.", 0),
    ("Candidates also write vague bullet points (\"Led the team\") instead of quantified, tailored ones.", 0),
    ("Goal: show a candidate, instantly, how well their resume matches a specific job — and help them fix the weak parts.", 0),
], size=20)
notes(s, "The problem: most resumes are screened by an ATS before a human sees them. If you're missing "
         "the job's keywords, you're filtered out. And people write vague bullets instead of quantified ones. "
         "This app gives instant, specific feedback on both.")

# ---------------------------------------------------------------- Slide 3 — What it does
s = add_slide()
title_bar(s, "What it does — the user flow")
tf = tbox(s, Inches(0.7), Inches(1.5), Inches(11.9), Inches(5))
bullets(tf, [
    ("1. Upload a resume (PDF or DOCX) and paste the target job description.", 0),
    ("2. Get an ATS match score (matched skills ÷ required skills) with the keywords you HAVE and the ones you're MISSING.", 0),
    ("3. Paste experience bullets; the app flags the unquantified ones and rewrites them with AI, tailored to the job.", 0),
    ("4. Every analysis is saved to a local database.", 0),
    ("Free features (parse + score) are open to all; the AI rewrite is access-controlled to protect usage.", 0),
], size=19)
notes(s, "The flow: upload a resume and paste a job description; get a match score with matched and missing "
         "keyword chips; then paste bullets and the app rewrites the weak ones with AI tailored to the job. "
         "Results are saved. The free scoring is open; the AI is token-protected so strangers can't burn my quota.")

# ---------------------------------------------------------------- Slide 4 — Tech stack
s = add_slide()
title_bar(s, "Tech stack")
tf = tbox(s, Inches(0.7), Inches(1.5), Inches(11.9), Inches(5))
bullets(tf, [
    ("Frontend: Next.js (React) — drag-and-drop upload, score visualizer, AI panel.", 0),
    ("Backend: Python + FastAPI, organized as a four-tier layered architecture.", 0),
    ("Domain logic: pure Python (keyword scoring, bullet auditing) — deterministic and fully unit-tested.", 0),
    ("AI: Google Gemini via Google AI Studio — the single external service, used only for rewriting.", 0),
    ("Storage: SQLite behind a repository interface.", 0),
    ("CI: GitHub Actions runs ruff (lint) + pytest on every push.", 0),
], size=19)
notes(s, "Next.js frontend, FastAPI backend in four tiers, pure-Python domain logic that's fully tested, "
         "Gemini only for the generative rewrite, SQLite for storage, and GitHub Actions CI running lint and tests.")

# ---------------------------------------------------------------- Slide 5 — Architecture (C4 container, text)
s = add_slide()
title_bar(s, "Architecture — n-tier (dependencies point down)")
tf = tbox(s, Inches(0.7), Inches(1.4), Inches(11.9), Inches(5.4))
bullets(tf, [
    ("Presentation — Next.js UI + FastAPI routes (/api/upload, /api/refine). Collects input, shows results, no business rules.", 0),
    ("Service — ResumeAnalysisService. Orchestrates one request across the tiers; holds no rules itself.", 0),
    ("Domain — ATSScorer (keyword match + score) and BulletPointAuditor (flags unquantified bullets). Pure, testable rules.", 0),
    ("Data — ParserFactory/PdfParser/DocxParser (parsing), GeminiAIClient (the AI call), ResumeRepository (SQLite).", 0),
    ("Rule: dependencies point DOWN only. Domain never imports FastAPI or the AI SDK — that's why it's 100% unit-testable.", 0),
], size=18)
notes(s, "Four tiers, dependencies pointing down only. Presentation collects and displays. Service orchestrates. "
         "Domain holds the pure business rules — scoring and auditing. Data isolates parsing, the AI call, and storage. "
         "Because Domain imports nothing external, it's fully unit-tested with no network or database.")

# ---------------------------------------------------------------- Slide 6 — Tier diagram (boxes)
s = add_slide()
title_bar(s, "Architecture — the tiers, visually")
tiers = [
    ("PRESENTATION", "Next.js UI  ·  FastAPI routes (/api/upload, /api/refine)", AQUA),
    ("SERVICE", "ResumeAnalysisService  (orchestration only)", RGBColor(0x4F, 0xB3, 0xB5)),
    ("DOMAIN", "ATSScorer  ·  BulletPointAuditor  (business rules)", PINK),
    ("DATA", "ParserFactory  ·  GeminiAIClient  ·  ResumeRepository (SQLite)", RGBColor(0xC0, 0x5B, 0x8E)),
]
top = Inches(1.5)
for name, desc, color in tiers:
    box = s.shapes.add_shape(1, Inches(1.6), top, Inches(10.1), Inches(1.15))
    box.fill.solid()
    box.fill.fore_color.rgb = color
    box.line.fill.background()
    box.shadow.inherit = False
    f = box.text_frame
    f.word_wrap = True
    f.margin_left = Inches(0.3)
    p = f.paragraphs[0]
    r = p.add_run(); r.text = name; r.font.bold = True; r.font.size = Pt(18); r.font.color.rgb = WHITE
    p2 = f.add_paragraph()
    r2 = p2.add_run(); r2.text = desc; r2.font.size = Pt(14); r2.font.color.rgb = WHITE
    top = top + Inches(1.33)
# downward arrow note
tf = tbox(s, Inches(1.6), Inches(6.9), Inches(10), Inches(0.5))
set_text(tf, "Dependencies flow downward only ↓", 14, MUTED, align=PP_ALIGN.CENTER)
notes(s, "Here are the four tiers as boxes. Presentation at top, then Service, Domain, Data. Each only depends on "
         "the tier below it. This is the same tier table that's in my README and design document.")

# ---------------------------------------------------------------- Slide 7 — Design decision defended
s = add_slide()
title_bar(s, "A design decision I defend")
tf = tbox(s, Inches(0.7), Inches(1.4), Inches(11.9), Inches(5.4))
set_text(tf, "Separate deterministic logic from the AI (ADR-001)", 22, AQUA_DARK, bold=True)
bullets(tf, [
    ("The scoring could have been handed entirely to the LLM — but that is slow, untestable, and non-deterministic.", 0),
    ("Decision: keyword scoring and bullet auditing are pure Python Domain rules (no AI). Gemini is used ONLY to rewrite bullets.", 0),
    ("Payoff: the core logic is 100% unit-tested and gives the same answer every time; the AI surface is small and isolated.", 0),
    ("Proof it paid off: when Google retired model names and throttled the free tier, swapping models was a ONE-LINE change in one Data-tier file — nothing in Service or Domain moved (Dependency Inversion).", 0),
], size=18)
notes(s, "The decision I'm most proud of: I did NOT hand scoring to the AI. Scoring and auditing are deterministic "
         "Python rules, fully tested. Gemini only rewrites bullets. The payoff showed up for real — when Google "
         "retired models and throttled the free tier, I fixed it by changing one line in one Data-tier file, because "
         "the AI call is isolated behind a client. That's Dependency Inversion doing its job.")

# ---------------------------------------------------------------- Slide 8 — SOLID & patterns
s = add_slide()
title_bar(s, "SOLID & design patterns — where they live")
tf = tbox(s, Inches(0.7), Inches(1.5), Inches(11.9), Inches(5))
bullets(tf, [
    ("Single Responsibility — one job per class (ATSScorer, BulletPointAuditor, parsers, GeminiAIClient, ResumeRepository).", 0),
    ("Open/Closed — document_parser.py: new file format = new subclass + registry entry, no edits to existing parsers.", 0),
    ("Dependency Inversion — ResumeAnalysisService takes scorer/auditor/AI client/repository INJECTED; tests pass fakes.", 0),
    ("Factory Method (pattern) — ParserFactory.get_parser() picks the parser per file type.", 0),
    ("Honest 'no fit': Abstract Factory, Builder, Prototype, Singleton — reasons documented in docs/pattern-map.md.", 0),
], size=18)
notes(s, "SOLID isn't name-dropped — each maps to a file. Single Responsibility across the classes. Open/Closed in the "
         "parser. Dependency Inversion in the service via constructor injection. Factory Method is the one creational "
         "pattern I actually needed; the others I honestly marked 'no fit' with reasons in pattern-map.md.")

# ---------------------------------------------------------------- Slide 9 — Quality & process
s = add_slide()
title_bar(s, "Quality & engineering process")
tf = tbox(s, Inches(0.7), Inches(1.5), Inches(11.9), Inches(5))
bullets(tf, [
    ("31 automated tests (pytest); the AI is mocked, so tests need no key and make no network calls.", 0),
    ("CI green on every push — GitHub Actions runs ruff + pytest.", 0),
    ("Work flows through issues → branches → pull requests → partner review → merge.", 0),
    ("Every AI-assisted PR carries a written critique block (what the AI got wrong, how I caught and fixed it).", 0),
    ("Unhappy paths handled: bad file type → 400; no/invalid AI token → 403; AI busy → model fallback + clear message.", 0),
], size=18)
notes(s, "Quality: 31 tests with the AI mocked so CI is fast and keyless. CI runs lint and tests on every push. I work "
         "through issues, branches, and reviewed PRs. Every AI-assisted PR has a critique block. And I handle the "
         "unhappy paths — wrong file type, missing token, and a busy AI service all fail cleanly.")

# ---------------------------------------------------------------- Slide 10 — Demo
s = add_slide(AQUA)
tf = tbox(s, Inches(1), Inches(2.6), Inches(11.3), Inches(2))
set_text(tf, "Live demo", 40, WHITE, bold=True, align=PP_ALIGN.CENTER)
set_text(tf, "Upload example_resume.pdf → see the match score & keywords → reject a .png (rule enforced) → rewrite a bullet with AI",
         18, WHITE, align=PP_ALIGN.CENTER, first=False)
notes(s, "For the demo I'll upload the example resume and the job description, show the match score and the matched/"
         "missing keyword chips, then try to upload a PNG to show the app refuse it (a rule enforced), and finally "
         "rewrite a weak bullet with the AI using my access token.")

# ---------------------------------------------------------------- Slide 11 — What's next
s = add_slide()
title_bar(s, "What I'd do next")
tf = tbox(s, Inches(0.7), Inches(1.5), Inches(11.9), Inches(5))
bullets(tf, [
    ("Surface stored analyses back to the user — a history screen reading from the SQLite repository.", 0),
    ("Smarter keyword extraction (synonyms, phrases) beyond the curated skills dictionary.", 0),
    ("Move AI to a paid/stable tier or add a second provider so the rewrite never depends on free-tier uptime.", 0),
    ("Add cover-letter generation (deliberately descoped for this deliverable — see ADR-001).", 0),
    ("Thank you! — repo, design document, and this deck all describe the same working system.", 0),
], size=18)
notes(s, "Next steps: a history screen reading from storage, smarter keyword extraction, a more stable AI tier or a "
         "second provider, and the descoped cover-letter feature. Thanks for watching — the repo, the document, and "
         "this deck all describe the same system.")

prs.save("CEN5064_Final_Presentation.pptx")
print("Saved CEN5064_Final_Presentation.pptx with", len(prs.slides.__iter__.__self__._sldIdLst), "slides")
