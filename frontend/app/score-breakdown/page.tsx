import Sidebar from "@/components/Sidebar";
import Link from "next/link";
import { parseScoreColor, formatScore } from "@/lib/api";
import fs from "fs";
import path from "path";

interface Row {
  candidate_id: string;
  rank: number;
  score: number;
  reasoning: string;
}

function loadSubmission(): Row[] {
  try {
    const csvPath = path.join(process.cwd(), "..", "submission.csv");
    if (!fs.existsSync(csvPath)) return [];
    const content = fs.readFileSync(csvPath, "utf-8");
    const lines = content.trim().split("\n").slice(1);
    return lines.map((line) => {
      const firstComma = line.indexOf(",");
      const secondComma = line.indexOf(",", firstComma + 1);
      const thirdComma = line.indexOf(",", secondComma + 1);
      const candidate_id = line.slice(0, firstComma).trim();
      const rank = parseInt(line.slice(firstComma + 1, secondComma).trim());
      const score = parseFloat(line.slice(secondComma + 1, thirdComma).trim());
      const reasoning = line.slice(thirdComma + 1).replace(/^"|"$/g, "").trim();
      return { candidate_id, rank, score, reasoning };
    });
  } catch {
    return [];
  }
}

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{label}</span>
        <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
          {(value * 100).toFixed(1)}%
        </span>
      </div>
      <div className="progress-bar" style={{ height: 8 }}>
        <div
          className="progress-fill"
          style={{ width: `${value * 100}%`, background: color, borderRadius: 4 }}
        />
      </div>
    </div>
  );
}

export default function ScoreBreakdown() {
  const rows = loadSubmission();
  const top20 = rows.slice(0, 20);

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar />
      <main style={{ flex: 1, padding: "32px 40px", overflow: "auto" }}>
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.03em" }}>
            Score Breakdown
          </h1>
          <p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
            Visual score distribution across ranking dimensions for top 20 candidates
          </p>
        </div>

        {/* Score distribution overview */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 32 }}>
          {[
            { label: "High Fit (≥85%)", count: rows.filter(r => r.score >= 0.85).length, color: "#B7D9B2" },
            { label: "Mid Fit (70-85%)", count: rows.filter(r => r.score >= 0.70 && r.score < 0.85).length, color: "#F2D6A2" },
            { label: "Lower Fit (<70%)", count: rows.filter(r => r.score < 0.70).length, color: "#FCA5A5" },
            { label: "Top Score", count: rows[0] ? `${(rows[0].score * 100).toFixed(1)}%` : "N/A", color: "#A8C5DA" },
          ].map((item) => (
            <div key={item.label} className="card stat-card">
              <div style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)" }}>{item.count}</div>
              <div style={{ fontSize: 11, letterSpacing: "0.06em", color: "var(--text-muted)", textTransform: "uppercase", marginTop: 4 }}>
                {item.label}
              </div>
              <div style={{ height: 3, background: item.color, borderRadius: 2, marginTop: 10 }} />
            </div>
          ))}
        </div>

        {/* Per-candidate score bars */}
        <div className="card">
          <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 20, color: "var(--text-primary)" }}>
            Top 20 Candidates — Score Profile
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
            {top20.map((row) => (
              <div key={row.candidate_id} style={{
                padding: 16,
                border: "1px solid var(--border)",
                borderRadius: 10,
                background: "var(--surface)",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <div>
                    <span style={{
                      display: "inline-block", width: 22, height: 22, borderRadius: "50%",
                      background: "var(--accent-light)", color: "var(--accent-dark)",
                      textAlign: "center", lineHeight: "22px", fontSize: 11, fontWeight: 700, marginRight: 8
                    }}>
                      {row.rank}
                    </span>
                    <Link href={`/candidate/${row.candidate_id}`} style={{ fontSize: 13, fontWeight: 600, color: "var(--accent-dark)", textDecoration: "none" }}>
                      {row.candidate_id}
                    </Link>
                  </div>
                  <span className={`score-badge ${parseScoreColor(row.score)}`}>
                    {formatScore(row.score)}%
                  </span>
                </div>
                <ScoreBar label="Overall Fit" value={row.score} color={row.score >= 0.85 ? "#B7D9B2" : row.score >= 0.70 ? "#F2D6A2" : "#FCA5A5"} />
                <p style={{ fontSize: 11, color: "var(--text-muted)", lineHeight: 1.5, marginTop: 8 }}>
                  {row.reasoning.slice(0, 100)}...
                </p>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
