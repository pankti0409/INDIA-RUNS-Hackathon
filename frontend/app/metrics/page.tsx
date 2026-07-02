import Sidebar from "@/components/Sidebar";

export default function Metrics() {
  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar />
      <main style={{ flex: 1, padding: "32px 40px" }}>
        <div style={{ marginBottom: 28 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.03em" }}>System Metrics</h1>
          <p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 13 }}>
            Ranking pipeline performance and configuration
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          {/* Runtime */}
          <div className="card">
            <h2 style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Runtime Performance</h2>
            {[
              ["Load 100K candidates", "~12s"],
              ["Score 100K candidates", "~54s"],
              ["Sort + write CSV", "<1s"],
              ["Total", "~66s"],
              ["Constraint", "≤300s (5 min)"],
            ].map(([label, value]) => (
              <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--border)", fontSize: 12 }}>
                <span style={{ color: "var(--text-secondary)" }}>{label}</span>
                <span style={{ fontWeight: 600, color: value === "~66s" ? "#065F46" : "var(--text-primary)" }}>
                  {value}
                </span>
              </div>
            ))}
          </div>

          {/* Constraints */}
          <div className="card">
            <h2 style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Compute Constraints</h2>
            {[
              ["CPU Only", "✓ Compliant"],
              ["≤16GB RAM", "✓ ~500MB peak"],
              ["No Network", "✓ Fully offline"],
              ["No GPU", "✓ CPU only"],
              ["No External APIs", "✓ Zero API calls"],
              ["Runtime ≤5min", "✓ ~66s actual"],
            ].map(([label, value]) => (
              <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--border)", fontSize: 12 }}>
                <span style={{ color: "var(--text-secondary)" }}>{label}</span>
                <span style={{ fontWeight: 600, color: "#065F46" }}>{value}</span>
              </div>
            ))}
          </div>

          {/* Scoring weights */}
          <div className="card">
            <h2 style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Scoring Weights</h2>
            {[
              ["Title / Role Match", 28],
              ["Core AI/Retrieval Skills", 22],
              ["Experience", 15],
              ["Behavioral Signals", 12],
              ["Education", 7],
              ["Platform Assessments", 6],
              ["Location", 5],
              ["GitHub / Open Source", 5],
            ].map(([label, pct]) => (
              <div key={label as string} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 4 }}>
                  <span style={{ color: "var(--text-secondary)" }}>{label}</span>
                  <span style={{ fontWeight: 600 }}>{pct}%</span>
                </div>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${pct as number * 3.3}%` }} />
                </div>
              </div>
            ))}
          </div>

          {/* Honeypot */}
          <div className="card">
            <h2 style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Honeypot Detection</h2>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 14, lineHeight: 1.6 }}>
              The dataset contains ~80 honeypot candidates with subtly impossible profiles. Our detection engine flags them via multiple signals.
            </p>
            {[
              ["Title-Skills Mismatch", "Disqualifier title + 5+ AI keywords"],
              ["Expert with 0 Months", "Claims expertise with zero usage duration"],
              ["Assessment vs Claim Gap", "Advanced claim but assessment score <40"],
              ["Timeline Inconsistency", "Career duration errors >12 months"],
              ["Unendorsed Skill Density", "15+ skills with avg <2 endorsements"],
            ].map(([label, desc]) => (
              <div key={label as string} style={{ marginBottom: 12, paddingBottom: 12, borderBottom: "1px solid var(--border)" }}>
                <div style={{ fontWeight: 500, fontSize: 12 }}>{label}</div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
