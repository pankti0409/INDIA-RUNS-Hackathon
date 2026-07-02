"use client";

import Sidebar from "@/components/Sidebar";
import { useState, useRef } from "react";

type ParsedCandidate = {
  candidate_id: string;
  extracted_profile: {
    name: string;
    current_title: string;
    location: string;
    years_of_experience: number;
    email: string;
    github_url?: string;
    linkedin_url?: string;
  };
  extracted_skills: string[];
  ranking_score: number;
  score_pct: string;
};

function DropZone({ onFile }: { onFile: (file: File) => void }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div
      id="resume-dropzone"
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const f = e.dataTransfer.files[0];
        if (f) onFile(f);
      }}
      style={{
        border: `2px dashed ${dragging ? "var(--accent-dark)" : "var(--border)"}`,
        borderRadius: 12,
        padding: "40px 24px",
        textAlign: "center",
        cursor: "pointer",
        transition: "all 0.2s",
        background: dragging ? "var(--bg)" : "transparent",
      }}
    >
      <div style={{ fontSize: 32, marginBottom: 12 }}>📄</div>
      <div style={{ fontWeight: 600, fontSize: 15, color: "var(--text-primary)", marginBottom: 6 }}>
        Drop resume here or click to browse
      </div>
      <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
        Supports: PDF, DOCX, TXT, CSV, XLSX, JSON — max 10MB
      </div>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.txt,.csv,.xlsx,.xls,.json,.jsonl"
        style={{ display: "none" }}
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); }}
      />
    </div>
  );
}

export default function ImportCandidates() {
  const [result, setResult] = useState<ParsedCandidate | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fileName, setFileName] = useState("");

  async function handleFile(file: File) {
    setFileName(file.name);
    setLoading(true);
    setError("");
    setResult(null);

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch("/api/resume/upload", { method: "POST", body: form });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload failed");
      }
      const data = await res.json();
      setResult(data);
    } catch (e: any) {
      setError(e.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar />
      <main style={{ flex: 1, padding: "32px 40px", overflow: "auto", maxWidth: 900 }}>
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.03em" }}>
            Import Candidates
          </h1>
          <p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
            Upload a resume in any format — we parse it and rank it against the AI/ML Engineer JD
          </p>
        </div>

        <div className="card" style={{ marginBottom: 24 }}>
          <DropZone onFile={handleFile} />
          {fileName && (
            <div style={{ marginTop: 12, fontSize: 12, color: "var(--text-muted)", textAlign: "center" }}>
              {loading ? "⏳ Parsing..." : `✓ ${fileName}`}
            </div>
          )}
        </div>

        {error && (
          <div style={{ padding: 16, background: "#fee2e2", borderRadius: 10, color: "#991b1b", fontSize: 13, marginBottom: 20 }}>
            ⚠️ {error}
          </div>
        )}

        {result && (
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
              <div>
                <div style={{ fontSize: 16, fontWeight: 700 }}>{result.extracted_profile.name}</div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
                  {result.extracted_profile.current_title}
                </div>
                <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                  {result.extracted_profile.location} · {result.extracted_profile.years_of_experience}yr exp
                </div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: result.ranking_score >= 0.7 ? "#16a34a" : result.ranking_score >= 0.5 ? "#d97706" : "#dc2626" }}>
                  {result.score_pct}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Fit Score</div>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
              {result.extracted_profile.email && (
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>📧 {result.extracted_profile.email}</div>
              )}
              {result.extracted_profile.github_url && (
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>
                  <a href={result.extracted_profile.github_url} target="_blank" rel="noreferrer" style={{ color: "var(--accent-dark)" }}>
                    🔗 GitHub
                  </a>
                </div>
              )}
            </div>

            <div>
              <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)", marginBottom: 8 }}>
                Extracted Skills ({result.extracted_skills.length})
              </div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {result.extracted_skills.map((skill) => (
                  <span key={skill} style={{
                    padding: "3px 10px", borderRadius: 20, fontSize: 11, fontWeight: 500,
                    background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text-secondary)"
                  }}>
                    {skill}
                  </span>
                ))}
              </div>
            </div>

            <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid var(--border)", fontSize: 11, color: "var(--text-muted)" }}>
              Candidate ID: {result.candidate_id}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
