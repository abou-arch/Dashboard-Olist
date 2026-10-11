import {
  ChartNoAxesCombined, Globe, House, Package, ShoppingBag, SmilePlus, Truck, Users, type LucideIcon,
} from "lucide-react";
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

const PAGES: { path: string; title: string; icon: LucideIcon; element: React.ReactNode }[] = [
  { path: "/", title: "Tableau de bord", icon: House, element: <Dashboard /> },
  { path: "/ventes", title: "Ventes", icon: ChartNoAxesCombined, element: <Sales /> },
  { path: "/clients", title: "Clients", icon: Users, element: <Customers /> },
  { path: "/produits", title: "Produits", icon: Package, element: <Products /> },
  { path: "/geographie", title: "Géographie", icon: Globe, element: <Geography /> },
  { path: "/satisfaction", title: "Satisfaction", icon: SmilePlus, element: <Satisfaction /> },
  { path: "/livraisons", title: "Livraisons", icon: Truck, element: <Deliveries /> },
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
      <NavLink to={{ pathname: "/", search }} className="brand" aria-label="Olist, tableau de bord">
        <Logo />
        <span className="brand-name">olist</span>
        <span className="brand-tagline">Analyse E-commerce</span>
      </NavLink>
      <nav className="nav" aria-label="Pages">
        {PAGES.map(({ path, title, icon: Icon }) => (
          <NavLink key={path} to={{ pathname: path, search }} end>
            <Icon size={20} strokeWidth={1.8} aria-hidden="true" />
            {title}
          </NavLink>
        ))}
      </nav>
      <div className="promo">
        <ShoppingBag size={64} strokeWidth={1.2} aria-hidden="true" />
        <strong>Données réelles Olist Brésil</strong>
        <p>Analyse complète des commandes, clients, produits et livraisons, 2016-2018.</p>
      </div>
    </aside>
  );
}

function Logo() {
  return (
    <svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true">
      <path d="M17 2 32 17 17 32 2 17Z" fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinejoin="round" />
      <path d="M17 2 32 17 17 17Z" fill="var(--accent)" opacity="0.9" />
      <path d="M2 17 17 17 17 32Z" fill="var(--accent-strong)" opacity="0.6" />
    </svg>
  );
}
