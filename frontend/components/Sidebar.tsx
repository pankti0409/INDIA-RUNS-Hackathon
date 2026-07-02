"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "@/components/ThemeProvider";

const NAV_LINKS = [
  { href: "/", label: "Dashboard", icon: "⬡" },
  { href: "/hackathon", label: "Rank Dataset", icon: "⚡" },
  { href: "/rankings", label: "Rankings", icon: "≡" },
  { href: "/import", label: "Import Candidate", icon: "📥" },
  { href: "/bulk-upload", label: "Bulk Upload", icon: "📁" },
  { href: "/jd-upload", label: "JD Upload", icon: "📋" },
  { href: "/gap-analysis", label: "Gap Analysis", icon: "🔍" },
  { href: "/resume-quality", label: "Resume Quality", icon: "🛡️" },
  { href: "/score-breakdown", label: "Score Breakdown", icon: "▦" },
  { href: "/behavioral", label: "Behavioral Analysis", icon: "◉" },
  { href: "/honeypots", label: "Honeypot Analysis", icon: "⚑" },
  { href: "/feature-importance", label: "Feature Importance", icon: "⬗" },
  { href: "/audit", label: "Ranking Audit", icon: "☰" },
  { href: "/metrics", label: "System Metrics", icon: "◈" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div
          style={{
            fontWeight: 700,
            fontSize: 16,
            letterSpacing: "-0.02em",
            color: "var(--text-primary)",
          }}
        >
          Redrob
        </div>
        <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
          Candidate Intelligence
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, overflowY: "auto" }}>
        {NAV_LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`sidebar-link ${pathname === link.href ? "active" : ""}`}
          >
            <span style={{ fontSize: 16, lineHeight: 1 }}>{link.icon}</span>
            {link.label}
          </Link>
        ))}
      </nav>

      {/* Theme toggle — global, persisted across all pages */}
      <div
        style={{
          padding: "16px 24px",
          borderTop: "1px solid var(--border)",
        }}
      >
        <button
          className="theme-toggle"
          onClick={toggle}
          id="theme-toggle-btn"
          aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
          title={isDark ? "Switch to light mode" : "Switch to dark mode"}
        >
          <span style={{ fontSize: 14 }}>{isDark ? "☀" : "◑"}</span>
          {isDark ? "Light mode" : "Dark mode"}
        </button>
      </div>
    </aside>
  );
}
