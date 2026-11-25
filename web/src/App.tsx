import { ArrowUpRight } from "lucide-react";
import { NavLink, Navigate, Route, Routes, useLocation } from "react-router";

import { Notice } from "./components/Page";
import { MetaProvider } from "./lib/data";
import { Customers } from "./pages/Customers";
import { Dashboard } from "./pages/Dashboard";
import { Deliveries } from "./pages/Deliveries";
import { Geography } from "./pages/Geography";
import { Products } from "./pages/Products";
import { Sales } from "./pages/Sales";
import { Satisfaction } from "./pages/Satisfaction";

const PORTFOLIO = "https://www.aboucamara.org";

const PAGES: { path: string; title: string; element: React.ReactNode }[] = [
  { path: "/", title: "Tableau de bord", element: <Dashboard /> },
  { path: "/ventes", title: "Ventes", element: <Sales /> },
  { path: "/clients", title: "Clients", element: <Customers /> },
  { path: "/produits", title: "Produits", element: <Products /> },
  { path: "/geographie", title: "Géographie", element: <Geography /> },
  { path: "/satisfaction", title: "Satisfaction", element: <Satisfaction /> },
  { path: "/livraisons", title: "Livraisons", element: <Deliveries /> },
];

export function App() {
  return (
    <MetaProvider>
      {(meta) => (
        <div className="app">
          <a className="skip-link" href="#contenu">Aller au contenu</a>
          <TopNav />
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
          <SiteFooter />
        </div>
      )}
    </MetaProvider>
  );
}

/** Barre flottante : marque, pages, lien vers le portfolio. */
function TopNav() {
  // Les filtres (dans l'adresse) suivent la navigation d'une page à l'autre.
  const { search } = useLocation();
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <NavLink to={{ pathname: "/", search }} className="brand" aria-label="Abou Camara, tableau de bord Olist">
          <Mark />
          <span className="brand-text">
            <strong>Abou Camara</strong>
            <span>Olist · Analyse e-commerce</span>
          </span>
        </NavLink>
        <nav className="nav" aria-label="Pages">
          {PAGES.map(({ path, title }) => (
            <NavLink key={path} to={{ pathname: path, search }} end>
              {title}
            </NavLink>
          ))}
        </nav>
        <a className="button button-dark nav-cta" href={PORTFOLIO}>
          Portfolio
          <ArrowUpRight size={16} aria-hidden="true" />
        </a>
      </div>
    </header>
  );
}

function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div className="site-footer-top">
          <div className="site-footer-brand">
            <Mark />
            <div>
              <strong>Abou Camara</strong>
              <p>Analyste de données. Je transforme les données d'une boutique en ligne en décisions claires.</p>
            </div>
          </div>
          <a className="button button-light" href={PORTFOLIO}>
            Voir le portfolio
            <ArrowUpRight size={16} aria-hidden="true" />
          </a>
        </div>
        <p className="site-footer-credits">
          Données : Olist, « Brazilian E-Commerce Public Dataset » (Kaggle, CC BY-NC-SA 4.0). Carte : @svg-maps/brazil
          (CC BY 4.0). Montants en réais (R$).
        </p>
        <div className="wordmark" aria-hidden="true">Olist</div>
      </div>
    </footer>
  );
}

/** Monogramme du portfolio : « A » et étoile. */
function Mark() {
  return (
    <svg className="mark" width="30" height="30" viewBox="0 0 64 64" aria-hidden="true">
      <path
        fill="currentColor"
        d="M30.2 5L33 10.6L16.8 55H13.2ZM30.2 5H35.8L52.8 55H43.6ZM22.9 37.2H39V40H21.9ZM9 53.6H21.2V56H9ZM38.6 53.6H57.4V56H38.6Z"
      />
      <path className="mark-star" d="M26 42.4Q26.6 47.1 31.3 47.7Q26.6 48.3 26 53Q25.4 48.3 20.7 47.7Q25.4 47.1 26 42.4Z" />
    </svg>
  );
}
