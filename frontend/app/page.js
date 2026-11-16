"use client";

import { useRef, useState } from "react";
import "./globals.css";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";
const ALLOWED = [".pdf", ".docx"];
const NEWLINE = String.fromCharCode(10);

export default function Home() {
  const [file, setFile] = useState(null);
  const [jobDescription, setJobDescription] = useState("");
  const [bullets, setBullets] = useState("");
  const [aiToken, setAiToken] = useState("");

  const [analysis, setAnalysis] = useState(null);
  const [revisions, setRevisions] = useState(null);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [loadingAnalyze, setLoadingAnalyze] = useState(false);
  const [loadingRefine, setLoadingRefine] = useState(false);

  const fileInput = useRef(null);

  // Client-side file-type check: reject anything that is not PDF/DOCX BEFORE
  // sending it to the backend (Issue #4 "Done when").
  function acceptFile(f) {
    if (!f) return;
    const name = f.name.toLowerCase();
    if (!ALLOWED.some((ext) => name.endsWith(ext))) {
      setError("Only PDF or DOCX files are allowed.");
      setFile(null);
      return;
    }
    setError("");
    setFile(f);
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    acceptFile(e.dataTransfer.files[0]);
  }

  async function analyze() {
    setError("");
    setAnalysis(null);
    setRevisions(null);
    if (!file) {
      setError("Please choose a PDF or DOCX resume first.");
      return;
    }
    setLoadingAnalyze(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("job_description", jobDescription);
      const res = await fetch(`${API_BASE}/api/upload`, { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Analysis failed.");
      } else {
        setAnalysis(data);
      }
    } catch (err) {
      setError("Could not reach the backend. Is it running on port 8000?");
    } finally {
      setLoadingAnalyze(false);
    }
  }

  async function refine() {
    setError("");
    setRevisions(null);
    const list = bullets
      .split(NEWLINE)
      .map((b) => b.trim())
      .filter((b) => b.length > 0);
    if (list.length === 0) {
      setError("Enter at least one bullet point (one per line) to rewrite.");
      return;
    }
    setLoadingRefine(true);
    // Abort the request if it takes longer than 40 seconds so the UI shows a
    // clear message instead of spinning on "Rewriting..." forever.
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 75000);
    try {
      const res = await fetch(`${API_BASE}/api/refine`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-AI-Token": aiToken },
        body: JSON.stringify({ bullets: list, job_description: jobDescription }),
        signal: controller.signal,
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "AI rewrite failed.");
      } else {
        setRevisions(data.revisions);
      }
    } catch (err) {
      if (err.name === "AbortError") {
        setError("The AI took too long to respond. Please try again.");
      } else {
        setError("Could not reach the backend. Is it running on port 8000?");
      }
    } finally {
      clearTimeout(timer);
      setLoadingRefine(false);
    }
  }

  return (
    <main className="container">
      <h1>AI Resume Optimizer & ATS Matcher</h1>
      <p className="subtitle">
        Upload a resume, paste a job description, and see how well they match,
        then rewrite weak bullet points with AI.
      </p>

      {error ? <p className="error">{error}</p> : null}

      {/* Step 1: upload + job description + analyze */}
      <section className="card">
        <label>1. Your resume (PDF or DOCX)</label>
        <div
          className={dragging ? "dropzone dragging" : "dropzone"}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => fileInput.current && fileInput.current.click()}
        >
          Drag and drop your resume here, or click to choose a file.
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.docx"
            style={{ display: "none" }}
            onChange={(e) => acceptFile(e.target.files[0])}
          />
          {file ? <div className="filename">Selected: {file.name}</div> : null}
        </div>

        <label>2. Target job description</label>
        <textarea
          rows={6}
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
          placeholder="Paste the job posting text here..."
        />

        <button onClick={analyze} disabled={loadingAnalyze}>
          {loadingAnalyze ? "Analyzing..." : "Analyze resume"}
        </button>
      </section>

      {/* Analysis results */}
      {analysis ? (
        <section className="card">
          <label>ATS keyword match</label>
          <div className="score">{analysis.ats_score}%</div>

          <label>Keywords you already have</label>
          {analysis.matched_keywords.length ? (
            <div className="chips">
              {analysis.matched_keywords.map((k) => (
                <span key={k} className="chip matched">
                  {k}
                </span>
              ))}
            </div>
          ) : (
            <p className="muted">None matched yet.</p>
          )}

          <label>Keywords you are missing</label>
          {analysis.missing_keywords.length ? (
            <div className="chips">
              {analysis.missing_keywords.map((k) => (
                <span key={k} className="chip missing">
                  {k}
                </span>
              ))}
            </div>
          ) : (
            <p className="muted">Nothing missing, great match!</p>
          )}
        </section>
      ) : null}

      {/* Step 2: AI rewrite of bullets */}
      <section className="card">
        <label>3. Rewrite bullet points with AI</label>
        <p className="muted">
          Paste your experience bullet points (one per line). The AI rewrites the
          ones that lack a quantified metric, tailored to the job above.
        </p>
        <textarea
          rows={5}
          value={bullets}
          onChange={(e) => setBullets(e.target.value)}
          placeholder="Led the backend team"
        />

        <label>AI access token</label>
        <input
          type="password"
          value={aiToken}
          onChange={(e) => setAiToken(e.target.value)}
          placeholder="Required to use the AI feature"
        />

        <button className="secondary" onClick={refine} disabled={loadingRefine}>
          {loadingRefine ? "Rewriting..." : "Rewrite with AI"}
        </button>
      </section>

      {/* Rewrite results */}
      {revisions ? (
        <section className="card">
          <label>AI-rewritten bullets (before and after)</label>
          {revisions.length ? (
            revisions.map((r, i) => (
              <div className="pair" key={i}>
                <div className="before">{r.before}</div>
                <div className="after">{r.after}</div>
              </div>
            ))
          ) : (
            <p className="muted">
              No bullets needed rewriting, they all already include a number.
            </p>
          )}
        </section>
      ) : null}
    </main>
  );
}
