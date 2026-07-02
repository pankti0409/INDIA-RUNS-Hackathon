import Sidebar from "@/components/Sidebar";
import fs from "fs";
import path from "path";

interface Candidate {
  candidate_id: string;
  redrob_signals?: {
    open_to_work_flag?: boolean;
    recruiter_response_rate?: number;
    notice_period_days?: number;
    profile_completeness_score?: number;
    avg_response_time_hours?: number;
    verified_email?: boolean;
    verified_phone?: boolean;
    linkedin_connected?: boolean;
    interview_completion_rate?: number;
    offer_acceptance_rate?: number;
    applications_submitted_30d?: number;
    saved_by_recruiters_30d?: number;
    connection_count?: number;
    endorsements_received?: number;
  };
}

function loadCandidates(): Candidate[] {
  try {
    const p = path.join(process.cwd(), "..", "candidates.jsonl");
    if (!fs.existsSync(p)) return [];
    const content = fs.readFileSync(p, "utf-8");
    const lines = content.trim().split("\n").slice(0, 2000); // sample 2K
    return lines.map((l) => JSON.parse(l));
  } catch {
    return [];
  }
}

function avg(arr: number[]) {
  if (!arr.length) return 0;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function pct(val: number) { return `${(val * 100).toFixed(1)}%`; }

function SignalRow({ label, value, unit = "" }: { label: string; value: string | number; unit?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
      <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>{value}{unit}</span>
    </div>
  );
}

function Bar({ label, value, max = 1 }: { label: string; value: number; max?: number }) {
  const pctVal = (value / max) * 100;
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>{label}</span>
        <span style={{ fontSize: 12, fontWeight: 600 }}>{pct(value / max)}</span>
      </div>
      <div className="progress-bar" style={{ height: 6 }}>
        <div className="progress-fill" style={{ width: `${pctVal}%`, borderRadius: 3 }} />
      </div>
    </div>
  );
}

export default function BehavioralAnalysis() {
  const candidates = loadCandidates();
  const sigs = candidates.map((c) => c.redrob_signals || {});

  const openToWork = sigs.filter((s) => s.open_to_work_flag).length;
  const avgResponseRate = avg(sigs.map((s) => s.recruiter_response_rate || 0));
  const avgNotice = avg(sigs.map((s) => s.notice_period_days || 90));
  const avgCompleteness = avg(sigs.map((s) => s.profile_completeness_score || 0));
  const verifiedEmail = sigs.filter((s) => s.verified_email).length;
  const verifiedPhone = sigs.filter((s) => s.verified_phone).length;
  const linkedinConnected = sigs.filter((s) => s.linkedin_connected).length;
  const avgInterviewCompletion = avg(sigs.map((s) => s.interview_completion_rate || 0));
  const avgOfferAcceptance = avg(sigs.filter((s) => (s.offer_acceptance_rate || -1) >= 0).map((s) => s.offer_acceptance_rate || 0));
  const avgApps = avg(sigs.map((s) => s.applications_submitted_30d || 0));
  const avgSaved = avg(sigs.map((s) => s.saved_by_recruiters_30d || 0));
  const total = candidates.length || 1;

  // Notice period buckets
  const noticeBuckets = [
    { label: "≤15 days", count: sigs.filter((s) => (s.notice_period_days || 90) <= 15).length },
    { label: "16–30 days", count: sigs.filter((s) => { const n = s.notice_period_days || 90; return n > 15 && n <= 30; }).length },
    { label: "31–60 days", count: sigs.filter((s) => { const n = s.notice_period_days || 90; return n > 30 && n <= 60; }).length },
    { label: "61–90 days", count: sigs.filter((s) => { const n = s.notice_period_days || 90; return n > 60 && n <= 90; }).length },
    { label: ">90 days", count: sigs.filter((s) => (s.notice_period_days || 90) > 90).length },
  ];

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar />
      <main style={{ flex: 1, padding: "32px 40px", overflow: "auto" }}>
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.03em" }}>
            Behavioral Analysis
          </h1>
          <p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
            Redrob behavioral signal distribution across {total.toLocaleString()} sampled candidates
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 20, marginBottom: 28 }}>
          {[
            { label: "Open to Work", value: `${openToWork.toLocaleString()}`, sub: `${pct(openToWork / total)} of sample` },
            { label: "Avg Response Rate", value: pct(avgResponseRate), sub: "Recruiter message reply rate" },
            { label: "Avg Notice Period", value: `${avgNotice.toFixed(0)}d`, sub: "Days to join" },
          ].map((s) => (
            <div key={s.label} className="card stat-card">
              <div style={{ fontSize: 26, fontWeight: 700 }}>{s.value}</div>
              <div style={{ fontSize: 11, letterSpacing: "0.06em", color: "var(--text-muted)", textTransform: "uppercase", marginTop: 4 }}>{s.label}</div>
              <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4 }}>{s.sub}</div>
            </div>
          ))}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          {/* Signal averages */}
          <div className="card">
            <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Availability & Engagement</h2>
            <Bar label="Profile Completeness" value={avgCompleteness / 100} />
            <Bar label="Interview Completion Rate" value={avgInterviewCompletion} />
            <Bar label="Offer Acceptance Rate" value={avgOfferAcceptance} />
            <Bar label="Recruiter Response Rate" value={avgResponseRate} />
            <div style={{ marginTop: 16, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
              <SignalRow label="Avg Applications / 30d" value={avgApps.toFixed(1)} />
              <SignalRow label="Avg Saved by Recruiters / 30d" value={avgSaved.toFixed(1)} />
            </div>
          </div>

          {/* Trust & verification */}
          <div className="card">
            <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Trust & Verification</h2>
            <SignalRow label="Verified Email" value={`${verifiedEmail.toLocaleString()} (${pct(verifiedEmail / total)})`} />
            <SignalRow label="Verified Phone" value={`${verifiedPhone.toLocaleString()} (${pct(verifiedPhone / total)})`} />
            <SignalRow label="LinkedIn Connected" value={`${linkedinConnected.toLocaleString()} (${pct(linkedinConnected / total)})`} />
            <h2 style={{ fontSize: 14, fontWeight: 600, margin: "20px 0 16px" }}>Notice Period Distribution</h2>
            {noticeBuckets.map((b) => (
              <Bar key={b.label} label={b.label} value={b.count / total} max={1} />
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
