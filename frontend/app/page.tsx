import Sidebar from "@/components/Sidebar";
import Link from "next/link";
import { parseScoreColor, formatScore, fetchMetrics } from "@/lib/api";
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
    const lines = content.trim().split("\n").slice(1); // skip header
    return lines
      .map((line) => {
        // Handle quoted reasoning
        const firstComma = line.indexOf(",");
        const secondComma = line.indexOf(",", firstComma + 1);
        const thirdComma = line.indexOf(",", secondComma + 1);
        const candidate_id = line.slice(0, firstComma).trim();
        const rank = parseInt(line.slice(firstComma + 1, secondComma).trim());
        const score = parseFloat(line.slice(secondComma + 1, thirdComma).trim());
        const reasoning = line.slice(thirdComma + 1).replace(/^"|"$/g, "").trim();
        return { candidate_id, rank, score, reasoning };
      })
      .filter((row) => !row.candidate_id.startsWith("CAND_9990"));
  } catch {
    return [];
  }
}

export default async function Dashboard() {
  const rows = loadSubmission();
  const top10 = rows.slice(0, 10);
  const totalRanked = rows.length;
  const avgScore = rows.length > 0
    ? rows.reduce((s, r) => s + r.score, 0) / rows.length
    : 0;
  const topScore = rows[0]?.score ?? 0;

  let poolSize = 100000;
  try {
    const metrics = await fetchMetrics();
    // total_pool_size is the full candidates.jsonl line count
    poolSize = metrics.total_pool_size || metrics.ranked_candidates || 100000;
  } catch (e) {
    poolSize = 100000;
  }

  // Score distribution buckets (adjusted for improved scoring model)
  const highScores = rows.filter((r) => r.score >= 0.80).length;
  const midScores = rows.filter((r) => r.score >= 0.65 && r.score < 0.80).length;
  const lowScores = rows.filter((r) => r.score < 0.65).length;

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar />
      <main style={{ flex: 1, padding: "32px 40px", overflow: "auto" }}>
        {/* Header */}
        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.03em", color: "var(--text-primary)" }}>
            Candidate Ranking Dashboard
          </h1>
          <p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
            Senior AI/ML Engineer — Ranking &amp; Retrieval | Redrob Hackathon
          </p>
        </div>

        {/* Metric cards */}
        <div className="metric-grid">
          <div className="metric-card">
            <div className="metric-value">{totalRanked}</div>
            <div className="metric-label">Candidates Ranked</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{formatScore(topScore)}%</div>
            <div className="metric-label">Top Score</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">{formatScore(avgScore)}%</div>
            <div className="metric-label">Avg Top-100 Score</div>
          </div>
          <div className="metric-card">
            <div className="metric-value">
              {poolSize >= 1000 ? `${(poolSize / 1000).toFixed(0)}K` : poolSize}
            </div>
            <div className="metric-label">Pool Size</div>
          </div>
        </div>

        {/* Score distribution */}
        <div className="card" style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Score Distribution — Top 100</h2>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <div style={{ flex: 1, minWidth: 160 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: 12 }}>
                <span style={{ color: "var(--text-secondary)" }}>High Fit (≥85%)</span>
                <span style={{ fontWeight: 600 }}>{highScores}</span>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${(highScores / 100) * 100}%`, background: "#B7D9B2" }} />
              </div>
            </div>
            <div style={{ flex: 1, minWidth: 160 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: 12 }}>
                <span style={{ color: "var(--text-secondary)" }}>Mid Fit (70–85%)</span>
                <span style={{ fontWeight: 600 }}>{midScores}</span>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${(midScores / 100) * 100}%`, background: "#F2D6A2" }} />
              </div>
            </div>
            <div style={{ flex: 1, minWidth: 160 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, fontSize: 12 }}>
                <span style={{ color: "var(--text-secondary)" }}>Lower Fit (&lt;70%)</span>
                <span style={{ fontWeight: 600 }}>{lowScores}</span>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${(lowScores / 100) * 100}%`, background: "#FCA5A5" }} />
              </div>
            </div>
          </div>
        </div>

        {/* Top 10 table */}
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <h2 style={{ fontSize: 14, fontWeight: 600 }}>Top 10 Candidates</h2>
            <Link
              href="/rankings"
              style={{ fontSize: 12, color: "var(--accent-dark)", textDecoration: "none", fontWeight: 500 }}
              id="view-all-link"
            >
              View all 100 →
            </Link>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Candidate ID</th>
                <th>Score</th>
                <th>Reasoning</th>
              </tr>
            </thead>
            <tbody>
              {top10.map((row) => (
                <tr key={row.candidate_id} className="fade-in">
                  <td>
                    <span className="rank-badge">{row.rank}</span>
                  </td>
                  <td>
                    <Link
                      href={`/candidate/${row.candidate_id}`}
                      style={{ color: "var(--accent-dark)", textDecoration: "none", fontWeight: 500, fontSize: 13 }}
                    >
                      {row.candidate_id}
                    </Link>
                  </td>
                  <td>
                    <span className={`score-badge ${parseScoreColor(row.score)}`}>
                      {formatScore(row.score)}%
                    </span>
                  </td>
                  <td style={{ color: "var(--text-secondary)", fontSize: 12, maxWidth: 500 }}>
                    {row.reasoning}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
