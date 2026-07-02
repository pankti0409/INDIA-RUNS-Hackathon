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
    return lines
      .map((line) => {
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

export default function Rankings() {
  const rows = loadSubmission();

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar />
      <main style={{ flex: 1, padding: "32px 40px", overflow: "auto" }}>
        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.03em" }}>
            Candidate Rankings
          </h1>
          <p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
            Top 100 candidates for Senior AI/ML Engineer role — ranked by fit score
          </p>
        </div>

        {/* Table */}
        <div className="card" style={{ padding: 0 }}>
          <table className="data-table" id="rankings-table">
            <thead>
              <tr>
                <th style={{ width: 64 }}>Rank</th>
                <th>Candidate</th>
                <th style={{ width: 100 }}>Score</th>
                <th>Reasoning</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.candidate_id}>
                  <td>
                    <span
                      className="rank-badge"
                      style={
                        row.rank <= 3
                          ? { background: "#A8C5DA", color: "#0C2D45" }
                          : {}
                      }
                    >
                      {row.rank}
                    </span>
                  </td>
                  <td>
                    <Link
                      href={`/candidate/${row.candidate_id}`}
                      style={{ color: "var(--accent-dark)", textDecoration: "none", fontWeight: 600, fontSize: 13 }}
                    >
                      {row.candidate_id}
                    </Link>
                  </td>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span className={`score-badge ${parseScoreColor(row.score)}`}>
                        {formatScore(row.score)}%
                      </span>
                    </div>
                    <div className="progress-bar" style={{ marginTop: 6, width: 72 }}>
                      <div
                        className="progress-fill"
                        style={{
                          width: `${row.score * 100}%`,
                          background:
                            row.score >= 0.80
                              ? "#B7D9B2"
                              : row.score >= 0.65
                              ? "#F2D6A2"
                              : "#FCA5A5",
                        }}
                      />
                    </div>
                  </td>
                  <td style={{ color: "var(--text-secondary)", fontSize: 12, lineHeight: 1.5, maxWidth: 500 }}>
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
