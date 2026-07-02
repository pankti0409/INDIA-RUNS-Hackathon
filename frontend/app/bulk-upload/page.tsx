"use client";

import Sidebar from "@/components/Sidebar";
import { useState, useRef } from "react";

type BulkResult = {
  rank: number;
  candidate_id: string;
  name: string;
  title: string;
  score: number;
  score_pct: string;
  reasoning: string;
  source_file: string;
};

export default function BulkUpload() {
  const [results, setResults] = useState<BulkResult[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<{ total: number; parsed: number } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  async function handleFiles(files: FileList) {
    setLoading(true);
    setResults([]);
    setErrors([]);
    setStats(null);

    const form = new FormData();
    Array.from(files).forEach((f) => form.append("files", f));

    try {
      const res = await fetch("/api/resume/bulk-upload", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");
      setResults(data.results || []);
      setErrors(data.errors || []);
      setStats({ total: data.total_uploaded, parsed: data.successfully_parsed });
    } catch (e: any) {
      setErrors([e.message]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar />
      <main style={{ flex: 1, padding: "32px 40px", overflow: "auto" }}>
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.03em" }}>
            Bulk Resume Upload
          </h1>
          <p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
            Upload up to 50 resumes at once — all parsed and ranked simultaneously
          </p>
        </div>

        <div
          className="card"
          style={{ marginBottom: 28 }}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
        >
          <div style={{
            border: `2px dashed ${dragging ? "var(--accent-dark)" : "var(--border)"}`,
            borderRadius: 10, padding: "40px 24px", textAlign: "center", cursor: "pointer", transition: "all 0.2s",
          }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>📁</div>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 6 }}>
              Drop multiple resumes here or click to browse
            </div>
            <div style={{ fontSize: 12, color: "var(--text-muted)" }}>PDF, DOCX, TXT — up to 50 files, 10MB each</div>
            {loading && <div style={{ marginTop: 12, fontSize: 13, color: "var(--accent-dark)" }}>⏳ Processing files...</div>}
          </div>
          <input ref={inputRef} type="file" multiple accept=".pdf,.docx,.txt,.csv,.xlsx,.json" style={{ display: "none" }}
            onChange={(e) => { if (e.target.files?.length) handleFiles(e.target.files); }} />
        </div>

        {stats && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 24 }}>
            <div className="card stat-card">
              <div style={{ fontSize: 26, fontWeight: 700 }}>{stats.total}</div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginTop: 4 }}>Files Uploaded</div>
            </div>
            <div className="card stat-card">
              <div style={{ fontSize: 26, fontWeight: 700 }}>{stats.parsed}</div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginTop: 4 }}>Successfully Parsed</div>
            </div>
            <div className="card stat-card">
              <div style={{ fontSize: 26, fontWeight: 700 }}>{errors.length}</div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginTop: 4 }}>Parse Errors</div>
            </div>
          </div>
        )}

        {errors.length > 0 && (
          <div className="card" style={{ marginBottom: 20, background: "#fff5f5", border: "1px solid #fecaca" }}>
            <h3 style={{ fontSize: 13, fontWeight: 600, color: "#dc2626", marginBottom: 8 }}>Parse Errors</h3>
            {errors.map((e, i) => <div key={i} style={{ fontSize: 12, color: "#991b1b" }}>• {e}</div>)}
          </div>
        )}

        {results.length > 0 && (
          <div className="card">
            <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Ranked Results</h2>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: 60 }}>Rank</th>
                  <th>Name / Title</th>
                  <th style={{ width: 100 }}>Score</th>
                  <th>Source File</th>
                  <th>Reasoning</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r) => (
                  <tr key={r.candidate_id}>
                    <td><span className="rank-badge">{r.rank}</span></td>
                    <td>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{r.name}</div>
                      <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{r.title}</div>
                    </td>
                    <td>
                      <span className={`score-badge ${r.score >= 0.7 ? "score-high" : r.score >= 0.5 ? "score-mid" : "score-low"}`}>
                        {r.score_pct}
                      </span>
                    </td>
                    <td style={{ fontSize: 11, color: "var(--text-muted)" }}>{r.source_file}</td>
                    <td style={{ fontSize: 11, color: "var(--text-secondary)", maxWidth: 300 }}>{r.reasoning.slice(0, 100)}…</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
