// Squelette commun des pages : en-tête (titre, filtres, profil), chargement,
// erreurs, sélection vide et pied de page.
import type { ReactNode } from "react";

import type { PageData } from "../lib/api";
import type { PageState } from "../lib/data";
import { dateLabel } from "../lib/format";
import { PeriodFilter, StatesFilter } from "./Filters";

/** Données d'une page chargée et non vide : en-tête + contenu propre à la page. */
export type Loaded<T> = PageData<T> & T;

interface Props<T> {
  title: string;
  intro: string;
  state: PageState<T>;
  children: (data: Loaded<T>) => ReactNode;
}

export function Page<T>({ title, intro, state, children }: Props<T>) {
  const data = state.data;
  let body: ReactNode;
  if (state.status === "error" && !data) {
    body = <Notice kind="error">{state.message}</Notice>;
  } else if (!data) {
    body = <Notice>Chargement des données…</Notice>;
  } else if (data.orders === 0) {
    body = <Notice>Aucune commande pour ces filtres.</Notice>;
  } else {
    body = (
      <>
        {state.status === "error" && <Notice kind="error">{state.message}</Notice>}
        {children(data as Loaded<T>)}
      </>
    );
  }

  return (
    <div className="page">
      {state.status === "loading" && <div className="loading-bar" role="progressbar" aria-label="Chargement" />}
      <header className="page-header">
        <div>
          <h1>{title}</h1>
          <p>{intro}</p>
        </div>
        <div className="header-tools">
          <div className="filters">
            <PeriodFilter />
            <StatesFilter />
          </div>
          <div className="profile" aria-label="Auteur du tableau de bord">
            <span className="avatar" aria-hidden="true">AC</span>
            <div>
              <strong>Abou Camara</strong>
              <span>Analyste de données</span>
            </div>
          </div>
        </div>
      </header>
      {body}
      <footer className="footer">
        Données : Olist, « Brazilian E-Commerce Public Dataset » (Kaggle, CC BY-NC-SA 4.0). Carte : @svg-maps/brazil
        (CC BY 4.0). Montants en réais (R$).
      </footer>
    </div>
  );
}

export function Notice({ children, kind }: { children: ReactNode; kind?: "error" }) {
  return (
    <div className="notice" data-kind={kind} role={kind === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

/** « vs 04/07/2017 – 31/12/2017 » si une période de comparaison existe. */
export function comparisonLabel(data: PageData<unknown>): string | null {
  const previous = data.period.previous;
  return previous ? `vs ${dateLabel(previous.start)} – ${dateLabel(previous.end)}` : null;
}

interface CardProps {
  title?: string;
  subtitle?: string;
  /** Élément à droite du titre : légende, lien, badge… */
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Card({ title, subtitle, aside, children, className = "" }: CardProps) {
  return (
    <section className={`card ${className}`}>
      {(title || aside) && (
        <div className="card-header">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p>{subtitle}</p>}
          </div>
          {aside}
        </div>
      )}
      {children}
    </section>
  );
}

export function Grid({ cols, children }: { cols: "4" | "3" | "2" | "main" | "even-3"; children: ReactNode }) {
  return <div className={`grid cols-${cols}`}>{children}</div>;
}
