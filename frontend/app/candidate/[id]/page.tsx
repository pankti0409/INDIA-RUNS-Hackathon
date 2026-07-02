import Sidebar from "@/components/Sidebar";
import Link from "next/link";
import { notFound } from "next/navigation";
import fs from "fs";
import path from "path";

function loadSubmissionRow(id: string) {
  try {
    const csvPath = path.join(process.cwd(), "..", "submission.csv");
    if (!fs.existsSync(csvPath)) return null;
    const content = fs.readFileSync(csvPath, "utf-8");
    const lines = content.trim().split("\n").slice(1);
    for (const line of lines) {
      if (line.startsWith(id + ",")) {
        const firstComma = line.indexOf(",");
        const secondComma = line.indexOf(",", firstComma + 1);
        const thirdComma = line.indexOf(",", secondComma + 1);
        const rank = parseInt(line.slice(firstComma + 1, secondComma).trim());
        const score = parseFloat(line.slice(secondComma + 1, thirdComma).trim());
        const reasoning = line.slice(thirdComma + 1).replace(/^"|"$/g, "").trim();
        return { rank, score, reasoning };
      }
    }
    return null;
  } catch { return null; }
}

async function loadCandidate(id: string) {
  try {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8124";
    const res = await fetch(`${apiBase}/api/candidate/${id}`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function CandidateDetail({
  params,
}: {
  params: { id: string };
}) {
  const { id } = params;
  const submissionRow = loadSubmissionRow(id);
  const candidate = await loadCandidate(id);

  if (!submissionRow) notFound();

  const profile = candidate?.profile ?? {};
  const skills = candidate?.skills ?? [];
  const career = candidate?.career_history ?? [];
  const education = candidate?.education ?? [];
  const signals = candidate?.redrob_signals ?? {};
  const certs = candidate?.certifications ?? [];

  const scorePercent = (submissionRow.score * 100).toFixed(1);
  const scoreColor = submissionRow.score >= 0.80 ? "#065F46" : submissionRow.score >= 0.65 ? "#92400E" : "#991B1B";
  const scoreBg = submissionRow.score >= 0.80 ? "#D1FAE5" : submissionRow.score >= 0.65 ? "#FEF3C7" : "#FEE2E2";

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar />
      <main style={{ flex: 1, padding: "32px 40px", overflow: "auto" }}>
        {/* Breadcrumb */}
        <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 20 }}>
          <Link href="/rankings" style={{ color: "var(--accent-dark)", textDecoration: "none" }}>Rankings</Link>
          {" / "}
          <span>{id}</span>
        </div>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 28 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
              <span className="rank-badge" style={{ width: 40, height: 40, fontSize: 14 }}>
                #{submissionRow.rank}
              </span>
              <h1 style={{ fontSize: 20, fontWeight: 700, letterSpacing: "-0.02em" }}>
                {profile.anonymized_name ?? id}
              </h1>
            </div>
            <p style={{ color: "var(--text-secondary)", fontSize: 13 }}>
              {profile.headline ?? profile.current_title ?? "—"}
            </p>
          </div>
          <span
            className="score-badge"
            style={{ background: scoreBg, color: scoreColor, fontSize: 18, padding: "6px 16px", borderRadius: 8 }}
          >
            {scorePercent}%
          </span>
        </div>

        {/* Reasoning */}
        <div className="card" style={{ marginBottom: 20, borderLeft: "3px solid var(--accent)" }}>
          <div style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-muted)", marginBottom: 8 }}>
            Ranking Reasoning
          </div>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7 }}>
            {submissionRow.reasoning}
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          {/* Profile info */}
          <div className="card">
            <h2 style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Profile</h2>
            <dl style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "8px 16px", fontSize: 12 }}>
              {[
                ["Title", profile.current_title],
                ["Company", profile.current_company],
                ["Location", `${profile.location}, ${profile.country}`],
                ["Experience", `${profile.years_of_experience} years`],
                ["Industry", profile.current_industry],
                ["Company Size", profile.current_company_size],
              ].map(([label, value]) => (
                <>
                  <dt style={{ color: "var(--text-muted)", fontWeight: 500 }}>{label}</dt>
                  <dd style={{ color: "var(--text-primary)" }}>{value ?? "—"}</dd>
                </>
              ))}
            </dl>
          </div>

          {/* Behavioral signals */}
          <div className="card">
            <h2 style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Behavioral Signals</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                ["Open to Work", signals.open_to_work_flag ? "✓ Yes" : "✗ No"],
                ["Last Active", signals.last_active_date ?? "—"],
                ["Recruiter Response Rate", `${((signals.recruiter_response_rate ?? 0) * 100).toFixed(0)}%`],
                ["Avg Response Time", `${(signals.avg_response_time_hours ?? 0).toFixed(0)}h`],
                ["Notice Period", `${signals.notice_period_days ?? "—"} days`],
                ["GitHub Score", signals.github_activity_score >= 0 ? `${signals.github_activity_score}/100` : "N/A"],
                ["Profile Completeness", `${signals.profile_completeness_score ?? 0}%`],
                ["Interview Completion", `${((signals.interview_completion_rate ?? 0) * 100).toFixed(0)}%`],
              ].map(([label, value]) => (
                <div key={label as string} style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                  <span style={{ color: "var(--text-muted)" }}>{label}</span>
                  <span style={{ fontWeight: 500, color: "var(--text-primary)" }}>{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Skills */}
          <div className="card">
            <h2 style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>
              Skills ({skills.length})
            </h2>
            <div style={{ display: "flex", flexWrap: "wrap" }}>
              {skills.map((s: { name: string; proficiency: string; endorsements: number }) => (
                <span key={s.name} className="skill-pill" title={`${s.proficiency} · ${s.endorsements} endorsements`}>
                  {s.name}
                </span>
              ))}
            </div>

            {/* Platform assessments */}
            {Object.keys(signals.skill_assessment_scores ?? {}).length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-muted)", marginBottom: 10 }}>
                  Platform Assessments
                </div>
                {Object.entries(signals.skill_assessment_scores ?? {}).map(([skill, score]) => (
                  <div key={skill} style={{ marginBottom: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 4 }}>
                      <span style={{ color: "var(--text-secondary)" }}>{skill}</span>
                      <span style={{ fontWeight: 600 }}>{score as number}/100</span>
                    </div>
                    <div className="progress-bar">
                      <div className="progress-fill" style={{ width: `${score as number}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Career history */}
          <div className="card">
            <h2 style={{ fontSize: 13, fontWeight: 600, marginBottom: 14 }}>Career History</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {career.slice(0, 4).map(
                (job: { title: string; company: string; start_date: string; end_date: string | null; duration_months: number; is_current: boolean }, i: number) => (
                  <div key={i} style={{ paddingLeft: 12, borderLeft: "2px solid var(--border)" }}>
                    <div style={{ fontWeight: 600, fontSize: 12 }}>{job.title}</div>
                    <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 2 }}>
                      {job.company} · {job.start_date?.slice(0, 7)} – {job.is_current ? "Present" : job.end_date?.slice(0, 7)}
                      {" "}({job.duration_months}mo)
                    </div>
                  </div>
                )
              )}
            </div>

            {/* Education */}
            {education.length > 0 && (
              <div style={{ marginTop: 20 }}>
                <div style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-muted)", marginBottom: 10 }}>
                  Education
                </div>
                {education.map(
                  (edu: { degree: string; field_of_study: string; institution: string; end_year: number; tier: string }, i: number) => (
                    <div key={i} style={{ fontSize: 12, marginBottom: 8 }}>
                      <div style={{ fontWeight: 500 }}>
                        {edu.degree} in {edu.field_of_study}
                      </div>
                      <div style={{ color: "var(--text-muted)", fontSize: 11 }}>
                        {edu.institution} · {edu.end_year} · {edu.tier}
                      </div>
                    </div>
                  )
                )}
              </div>
            )}

            {/* Certs */}
            {certs.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text-muted)", marginBottom: 8 }}>
                  Certifications
                </div>
                {certs.map((c: { name: string; issuer: string; year: number }, i: number) => (
                  <div key={i} style={{ fontSize: 12, marginBottom: 4 }}>
                    {c.name} <span style={{ color: "var(--text-muted)" }}>· {c.issuer} · {c.year}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
