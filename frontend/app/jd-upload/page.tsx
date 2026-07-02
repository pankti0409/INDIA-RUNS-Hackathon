"use client";

import Sidebar from "@/components/Sidebar";
import { useState, useRef } from "react";

type ParsedJD = {
  job_title: string;
  seniority: string;
  required_skills: string[];
  nice_to_have_skills: string[];
  years_of_experience_min: number;
  years_of_experience_max: number;
  location: string;
  work_mode: string;
  product_company_preferred: boolean;
  key_responsibilities: string[];
  disqualifiers: string[];
};

function Badge({ text, color }: { text: string; color: string }) {
  return (
    <span style={{
      display: "inline-block", padding: "3px 10px", borderRadius: 20,
      fontSize: 11, fontWeight: 500, background: color, marginRight: 6, marginBottom: 6,
      color: "var(--text-primary)",
    }}>
      {text}
    </span>
  );
}

export default function JDUpload() {
  const [mode, setMode] = useState<"text" | "file">("text");
  const [jdText, setJdText] = useState("");
  const [result, setResult] = useState<ParsedJD | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  async function parseText() {
    if (!jdText.trim()) return;
    setLoading(true); setError(""); setResult(null);
    try {
      const form = new FormData();
      form.append("jd_text", jdText);
      const res = await fetch("/api/jd/parse", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setResult(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function parseFile(file: File) {
    setLoading(true); setError(""); setResult(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch("/api/jd/parse", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setResult(data);
    } catch (e: any) {
      setError(e.message);
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
            JD Upload
          </h1>
          <p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
            Upload or paste a job description — we extract structured requirements and re-rank candidates
          </p>
        </div>

        {/* Mode selector */}
        <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
          {["text", "file"].map((m) => (
            <button
              key={m}
              onClick={() => setMode(m as "text" | "file")}
              style={{
                padding: "8px 18px", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer", border: "none",
                background: mode === m ? "var(--accent-dark)" : "var(--surface)",
                color: mode === m ? "#fff" : "var(--text-primary)",
              }}
            >
              {m === "text" ? "📝 Paste Text" : "📄 Upload File"}
            </button>
          ))}
        </div>

        <div className="card" style={{ marginBottom: 24 }}>
          {mode === "text" ? (
            <div>
              <textarea
                id="jd-text-input"
                placeholder="Paste your job description here..."
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                style={{
                  width: "100%", minHeight: 200, padding: 16, fontSize: 13, lineHeight: 1.6,
                  background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 8,
                  color: "var(--text-primary)", resize: "vertical", outline: "none",
                }}
              />
              <button
                id="parse-jd-btn"
                onClick={parseText}
                disabled={loading || !jdText.trim()}
                style={{
                  marginTop: 12, padding: "10px 24px", borderRadius: 8, fontSize: 13, fontWeight: 600,
                  background: "var(--accent-dark)", color: "#fff", border: "none", cursor: "pointer",
                  opacity: loading ? 0.6 : 1,
                }}
              >
                {loading ? "Parsing..." : "Parse JD"}
              </button>
            </div>
          ) : (
            <div
              onClick={() => fileRef.current?.click()}
              style={{
                border: "2px dashed var(--border)", borderRadius: 10, padding: "40px 24px",
                textAlign: "center", cursor: "pointer",
              }}
            >
              <div style={{ fontSize: 36, marginBottom: 12 }}>📋</div>
              <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 6 }}>Upload JD file</div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>PDF, DOCX, or TXT</div>
              {loading && <div style={{ marginTop: 10, fontSize: 13, color: "var(--accent-dark)" }}>Parsing...</div>}
              <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" style={{ display: "none" }}
                onChange={(e) => { const f = e.target.files?.[0]; if (f) parseFile(f); }} />
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
                <div style={{ fontSize: 16, fontWeight: 700 }}>{result.job_title}</div>
                <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 4 }}>
                  {result.seniority} · {result.location} · {result.work_mode}
                  · {result.years_of_experience_min}–{result.years_of_experience_max}yr
                </div>
              </div>
              {result.product_company_preferred && (
                <span style={{ padding: "4px 10px", background: "#dbeafe", color: "#1e40af", borderRadius: 20, fontSize: 11, fontWeight: 600 }}>
                  Product Co. Preferred
                </span>
              )}
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Required Skills</div>
              <div>{result.required_skills.map((s) => <Badge key={s} text={s} color="var(--accent-light)" />)}</div>
            </div>

            {result.nice_to_have_skills?.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Nice to Have</div>
                <div>{result.nice_to_have_skills.map((s) => <Badge key={s} text={s} color="var(--surface)" />)}</div>
              </div>
            )}

            {result.key_responsibilities?.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Key Responsibilities</div>
                {result.key_responsibilities.map((r, i) => (
                  <div key={i} style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>• {r}</div>
                ))}
              </div>
            )}

            {result.disqualifiers?.length > 0 && (
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#dc2626", marginBottom: 8 }}>Disqualifiers</div>
                {result.disqualifiers.map((d, i) => (
                  <div key={i} style={{ fontSize: 12, color: "#991b1b", marginBottom: 4 }}>⚠️ {d}</div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
