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

function loadAllCandidates(limit = 5000): any[] {
  try {
    const p = path.join(process.cwd(), "..", "candidates.jsonl");
    if (!fs.existsSync(p)) return [];
    const content = fs.readFileSync(p, "utf-8");
    return content.trim().split("\n").slice(0, limit).map((l) => JSON.parse(l));
  } catch {
    return [];
  }
}

function RiskBadge({ level }: { level: "high" | "medium" | "low" }) {
  const cfg = {
    high: { bg: "#fee2e2", color: "#991b1b", text: "High Risk" },
    medium: { bg: "#fef3c7", color: "#92400e", text: "Medium Risk" },
    low: { bg: "#d1fae5", color: "#065f46", text: "Clean" },
  }[level];
  return (
    <span style={{ padding: "2px 8px", borderRadius: 10, fontSize: 11, fontWeight: 600, background: cfg.bg, color: cfg.color }}>
      {cfg.text}
    </span>
  );
}

export default function HoneypotAnalysis() {
  const submission = loadSubmission();
  const allCandidates = loadAllCandidates(5000);

  // Honeypot patterns from submission reasoning
  const withConcerns = submission.filter((r) =>
    r.reasoning.toLowerCase().includes("concern") ||
    r.reasoning.toLowerCase().includes("inconsisten")
  );

  // From all candidates — detect keyword stuffers (skill count outlier)
  const skillCounts = allCandidates.map((c) => (c.skills || []).length);
  const avgSkills = skillCounts.reduce((a, b) => a + b, 0) / Math.max(1, skillCounts.length);
  const keywordStuffers = allCandidates.filter((c) => (c.skills || []).length > avgSkills * 2.5).length;

  // Profile completeness outliers (too-perfect = synthetic)
  const perfectProfiles = allCandidates.filter((c) => {
    const sig = c.redrob_signals || {};
    return sig.profile_completeness_score === 100 && sig.recruiter_response_rate === 1.0;
  }).length;

  // Impossible YoE: title "Senior" with < 2 years experience
  const impossibleSeniority = allCandidates.filter((c) => {
    const title = (c.profile?.current_title || "").toLowerCase();
    const yoe = c.profile?.years_of_experience || 0;
    return (title.includes("senior") || title.includes("principal")) && yoe < 2;
  }).length;

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar />
      <main style={{ flex: 1, padding: "32px 40px", overflow: "auto" }}>
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.03em" }}>
            Honeypot Analysis
          </h1>
          <p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
            Detected synthetic / manipulated profiles — excluded from top rankings
          </p>
        </div>

        {/* Stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 28 }}>
          {[
            { label: "Keyword Stuffers", value: keywordStuffers, desc: "Skill count > 2.5× average" },
            { label: "Perfect Profiles", value: perfectProfiles, desc: "100% complete + 100% response" },
            { label: "Impossible Seniority", value: impossibleSeniority, desc: "Senior title with <2yr exp" },
            { label: "In Top-100 with Concern", value: withConcerns.length, desc: "Flagged in submission" },
          ].map((item) => (
            <div key={item.label} className="card stat-card">
              <div style={{ fontSize: 26, fontWeight: 700, color: item.value > 0 ? "#dc2626" : "var(--text-primary)" }}>
                {item.value.toLocaleString()}
              </div>
              <div style={{ fontSize: 11, letterSpacing: "0.06em", color: "var(--text-muted)", textTransform: "uppercase", marginTop: 4 }}>
                {item.label}
              </div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 4 }}>{item.desc}</div>
            </div>
          ))}
        </div>

        {/* Detection methodology */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 28 }}>
          <div className="card">
            <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Detection Signals</h2>
            {[
              { signal: "Skill count > 2.5× dataset average", weight: "High", pattern: "Keyword Stuffer" },
              { signal: "100% completeness + 100% response rate", weight: "High", pattern: "Synthetic Profile" },
              { signal: "Senior title with <2yr experience", weight: "High", pattern: "Impossible Seniority" },
              { signal: "100+ endorsements with 0 connections", weight: "Medium", pattern: "Fabricated Social Proof" },
              { signal: "All skills listed at 'Expert' level", weight: "Medium", pattern: "Skill Inflation" },
              { signal: "Active in >20 assessments with perfect scores", weight: "Medium", pattern: "Score Gaming" },
              { signal: "0-day notice + perfect availability + high response", weight: "Low", pattern: "Behavioral Twin" },
            ].map((item) => (
              <div key={item.signal} style={{ display: "flex", gap: 12, padding: "10px 0", borderBottom: "1px solid var(--border)", alignItems: "flex-start" }}>
                <span style={{ fontSize: 11, fontWeight: 600, padding: "2px 6px", borderRadius: 4, background: item.weight === "High" ? "#fee2e2" : item.weight === "Medium" ? "#fef3c7" : "#f3f4f6", color: item.weight === "High" ? "#991b1b" : item.weight === "Medium" ? "#92400e" : "#374151", flexShrink: 0 }}>
                  {item.weight}
                </span>
                <div>
                  <div style={{ fontSize: 12, color: "var(--text-primary)", marginBottom: 2 }}>{item.signal}</div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{item.pattern}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Flagged in top-100 */}
          <div className="card">
            <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Top-100 Profile Concerns</h2>
            {withConcerns.length === 0 ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--text-muted)", fontSize: 13 }}>
                ✓ No honeypot concerns in top-100 ranking
              </div>
            ) : (
              withConcerns.map((row) => (
                <div key={row.candidate_id} style={{ padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--accent-dark)" }}>{row.candidate_id}</span>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Rank #{row.rank}</span>
                      <RiskBadge level="medium" />
                    </div>
                  </div>
                  <p style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5 }}>
                    {row.reasoning.slice(0, 120)}...
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* All top-100 clean view */}
        <div className="card">
          <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Top-100 — Honeypot Risk Assessment</h2>
          <div className="data-table" style={{ overflow: "auto" }}>
            <table className="data-table" style={{ width: "100%" }}>
              <thead>
                <tr>
                  <th style={{ width: 60 }}>Rank</th>
                  <th>Candidate</th>
                  <th style={{ width: 90 }}>Score</th>
                  <th style={{ width: 110 }}>Risk Level</th>
                </tr>
              </thead>
              <tbody>
                {submission.map((row) => {
                  const hasConcern = row.reasoning.toLowerCase().includes("concern");
                  return (
                    <tr key={row.candidate_id}>
                      <td><span className="rank-badge">{row.rank}</span></td>
                      <td style={{ fontSize: 13, fontWeight: 600, color: "var(--accent-dark)" }}>{row.candidate_id}</td>
                      <td><span className={`score-badge ${parseScoreColor(row.score)}`}>{formatScore(row.score)}%</span></td>
                      <td><RiskBadge level={hasConcern ? "medium" : "low"} /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
