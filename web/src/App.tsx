import { NavLink, Navigate, Route, Routes, useLocation } from "react-router";

import { Notice } from "./components/Page";
import { MetaProvider } from "./lib/data";
import { useTheme, type ThemePreference } from "./lib/theme";
import { Customers } from "./pages/Customers";
import { Logistics } from "./pages/Logistics";
import { Overview } from "./pages/Overview";
import { Satisfaction } from "./pages/Satisfaction";
import { Sellers } from "./pages/Sellers";

const PAGES = [
  { path: "/", title: "Vue d'ensemble", icon: "M4 4h7v7H4zM13 4h7v4h-7zM13 10h7v10h-7zM4 13h7v7H4z", element: <Overview /> },
  { path: "/logistique", title: "Logistique", icon: "M3 6h11v10H3zM14 9h4l3 3v4h-7zM7 19a2 2 0 1 0 0-.01M17 19a2 2 0 1 0 0-.01", element: <Logistics /> },
  { path: "/satisfaction", title: "Satisfaction", icon: "M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z", element: <Satisfaction /> },
  { path: "/vendeurs", title: "Vendeurs et catégories", icon: "M4 9l1.5-5h13L20 9M4 9v11h16V9M4 9h16M9 20v-6h6v6", element: <Sellers /> },
  { path: "/clients", title: "Clients", icon: "M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21c0-4 3-6 7-6s7 2 7 6M16 3.5a4 4 0 0 1 0 7.5M22 21c0-3-1.5-5-4-5.7", element: <Customers /> },
];

export function App() {
  return (
    <MetaProvider>
      {(meta) => (
        <div className="app">
          <Sidebar />
          <main className="main" id="contenu">
            {meta.status === "ready" ? (
              <Routes>
                {PAGES.map((page) => (
                  <Route key={page.path} path={page.path} element={page.element} />
                ))}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            ) : (
              <div className="page">
                {meta.status === "error" ? (
                  <Notice kind="error">L'API ne répond pas ({meta.message}). Est-elle lancée ?</Notice>
                ) : (
                  <Notice>Chargement…</Notice>
                )}
              </div>
            )}
          </main>
        </div>
      )}
    </MetaProvider>
  );
}

function Sidebar() {
  // Les filtres (dans l'adresse) suivent la navigation d'une page à l'autre.
  const { search } = useLocation();
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 32 32"><path d="M8 24V14M14 24V8M20 24v-7M26 24V11" stroke="currentColor" strokeWidth="3.5" strokeLinecap="round" /></svg>
        </span>
        Dashboard Olist
      </div>
      <nav className="nav" aria-label="Pages">
        {PAGES.map((page) => (
          <NavLink key={page.path} to={{ pathname: page.path, search }} end>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" aria-hidden="true">
              <path d={page.icon} />
            </svg>
            {page.title}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        <ThemeSwitch />
        <span className="source">Place de marché brésilienne, 2016-2018. Montants en réais (R$).</span>
      </div>
    </aside>
  );
}

const THEMES: { value: ThemePreference; label: string }[] = [
  { value: "system", label: "Auto" },
  { value: "light", label: "Clair" },
  { value: "dark", label: "Sombre" },
];

function ThemeSwitch() {
  const { preference, setPreference } = useTheme();
  return (
    <div className="theme-switch" role="group" aria-label="Thème">
      {THEMES.map((theme) => (
        <button
          key={theme.value}
          type="button"
          aria-pressed={preference === theme.value}
          onClick={() => setPreference(theme.value)}
        >
          {theme.label}
        </button>
      ))}
    </div>
  );
}
