import Sidebar from "@/components/Sidebar";
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

function loadAuditReport(): string {
  try {
    const p = path.join(process.cwd(), "..", "ranking_audit_report.md");
    if (!fs.existsSync(p)) return "";
    return fs.readFileSync(p, "utf-8");
  } catch {
    return "";
  }
}

function parseMarkdownTable(md: string, header: string): { headers: string[]; rows: string[][] } | null {
  const lines = md.split("\n");
  let inTable = false;
  const headers: string[] = [];
  const rows: string[][] = [];
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes(header)) { inTable = true; }
    if (inTable && lines[i].startsWith("|") && !lines[i].includes("---")) {
      const cells = lines[i].split("|").filter((c) => c.trim()).map((c) => c.trim());
      if (headers.length === 0) { headers.push(...cells); }
      else { rows.push(cells); }
    } else if (inTable && !lines[i].startsWith("|") && headers.length > 0) {
      break;
    }
  }
  return headers.length > 0 ? { headers, rows } : null;
}

export default function RankingAudit() {
  const rows = loadSubmission();
  const auditMd = loadAuditReport();

  const scoreTable = parseMarkdownTable(auditMd, "Score Distribution");
  const titleTable = parseMarkdownTable(auditMd, "Title Distribution");
  const expTable = parseMarkdownTable(auditMd, "Experience Distribution");
  const locationTable = parseMarkdownTable(auditMd, "Location Distribution");
  const honeypotTable = parseMarkdownTable(auditMd, "Honeypot Analysis");
  const featureTable = parseMarkdownTable(auditMd, "Feature Contribution");

  function AuditTable({ title, data }: { title: string; data: { headers: string[]; rows: string[][] } | null }) {
    if (!data) return <div style={{ color: "var(--text-muted)", fontSize: 13 }}>No data available</div>;
    return (
      <div>
        <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: "var(--text-primary)" }}>{title}</h3>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr>
              {data.headers.map((h) => (
                <th key={h} style={{ textAlign: "left", padding: "6px 12px", background: "var(--bg)", color: "var(--text-muted)", fontSize: 11, letterSpacing: "0.05em", textTransform: "uppercase", borderBottom: "1px solid var(--border)" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, i) => (
              <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                {row.map((cell, j) => (
                  <td key={j} style={{ padding: "8px 12px", color: "var(--text-secondary)" }}>
                    {cell.replace(/\*\*/g, "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar />
      <main style={{ flex: 1, padding: "32px 40px", overflow: "auto" }}>
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.03em" }}>
            Ranking Audit
          </h1>
          <p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
            Distribution analysis, bias check, and feature contribution across top-100 candidates
          </p>
        </div>

        {/* Summary stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 28 }}>
          {[
            { label: "Candidates Ranked", value: rows.length },
            { label: "Score Range", value: rows.length > 0 ? `${(rows[rows.length - 1].score * 100).toFixed(1)}–${(rows[0].score * 100).toFixed(1)}%` : "N/A" },
            { label: "Avg Score", value: rows.length > 0 ? `${(rows.reduce((a, b) => a + b.score, 0) / rows.length * 100).toFixed(1)}%` : "N/A" },
            { label: "Runtime", value: "89.8s" },
          ].map((item) => (
            <div key={item.label} className="card stat-card">
              <div style={{ fontSize: 22, fontWeight: 700 }}>{item.value}</div>
              <div style={{ fontSize: 11, letterSpacing: "0.06em", color: "var(--text-muted)", textTransform: "uppercase", marginTop: 4 }}>{item.label}</div>
            </div>
          ))}
        </div>

        {/* Distribution tables */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
          <div className="card"><AuditTable title="Score Distribution" data={scoreTable} /></div>
          <div className="card"><AuditTable title="Experience Distribution" data={expTable} /></div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
          <div className="card"><AuditTable title="Title Distribution" data={titleTable} /></div>
          <div className="card"><AuditTable title="Location Distribution" data={locationTable} /></div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
          <div className="card"><AuditTable title="Honeypot Risk Analysis" data={honeypotTable} /></div>
          <div className="card"><AuditTable title="Feature Contribution (Top-100 Avg)" data={featureTable} /></div>
        </div>

        {/* Raw ranking */}
        <div className="card">
          <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Full Top-100 Ranking</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 64 }}>Rank</th>
                <th>Candidate ID</th>
                <th style={{ width: 90 }}>Score</th>
                <th>Reasoning</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.candidate_id}>
                  <td><span className="rank-badge" style={row.rank <= 3 ? { background: "#A8C5DA", color: "#0C2D45" } : {}}>{row.rank}</span></td>
                  <td style={{ fontWeight: 600, fontSize: 13, color: "var(--accent-dark)" }}>{row.candidate_id}</td>
                  <td><span className={`score-badge ${parseScoreColor(row.score)}`}>{formatScore(row.score)}%</span></td>
                  <td style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5 }}>{row.reasoning.slice(0, 120)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
