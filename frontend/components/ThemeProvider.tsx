"use client";

import { createContext, useContext, useEffect, useState } from "react";

type Theme = "light" | "dark";

interface ThemeContextValue {
  theme: Theme;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: "light",
  toggle: () => {},
});

export function useTheme() {
  return useContext(ThemeContext);
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  // On mount: read from localStorage (or system preference)
  useEffect(() => {
    const stored = localStorage.getItem("rr-theme") as Theme | null;
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const initial: Theme = stored ?? (prefersDark ? "dark" : "light");
    setTheme(initial);
    document.documentElement.classList.toggle("dark", initial === "dark");
    setMounted(true);
  }, []);

  const toggle = () => {
    setTheme((prev) => {
      const next: Theme = prev === "light" ? "dark" : "light";
      document.documentElement.classList.toggle("dark", next === "dark");
      localStorage.setItem("rr-theme", next);
      return next;
    });
  };

  // Avoid flash on initial load — render children immediately,
  // but suppress any theme-dependent UI until mounted
  return (
    <ThemeContext.Provider value={{ theme, toggle }}>
      {/* Inject a tiny inline script to apply the theme class before paint (no-flash) */}
      <script
        dangerouslySetInnerHTML={{
          __html: `
            (function(){
              try {
                var t = localStorage.getItem('rr-theme');
                var dark = t === 'dark' || (!t && window.matchMedia('(prefers-color-scheme: dark)').matches);
                if (dark) document.documentElement.classList.add('dark');
              } catch(e) {}
            })();
          `,
        }}
      />
      {children}
    </ThemeContext.Provider>
  );
}
