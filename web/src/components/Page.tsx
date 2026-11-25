// Squelette commun des pages : en-tête (titre, filtres), chargement, erreurs
// et sélection vide.
import type { ReactNode } from "react";

import type { PageData } from "../lib/api";
import type { PageState } from "../lib/data";
import { dateLabel } from "../lib/format";
import { PeriodFilter, StatesFilter } from "./Filters";

/** Données d'une page chargée et non vide : en-tête + contenu propre à la page. */
export type Loaded<T> = PageData<T> & T;

interface Props<T> {
  title: string;
  /** Seconde partie du titre, en ton adouci (comme sur le portfolio). */
  lead: string;
  intro: string;
  state: PageState<T>;
  children: (data: Loaded<T>) => ReactNode;
}

export function Page<T>({ title, lead, intro, state, children }: Props<T>) {
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
        <span className="eyebrow">Olist · Brésil 2016–2018</span>
        <h1>
          {title}. <span>{lead}</span>
        </h1>
        <div className="page-header-row">
          <p>{intro}.</p>
          <div className="filters" role="group" aria-label="Filtres">
            <PeriodFilter />
            <StatesFilter />
          </div>
        </div>
      </header>
      <div className="page-body">{body}</div>
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
