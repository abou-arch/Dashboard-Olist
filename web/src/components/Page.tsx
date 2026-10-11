// Squelette commun des pages : titre, filtres, chargement, erreurs, sélection vide.
import type { ReactNode } from "react";

import type { PageData } from "../lib/api";
import type { PageState } from "../lib/data";
import { dateLabel } from "../lib/format";
import { FilterBar } from "./FilterBar";

/** Données d'une page chargée et non vide : en-tête + contenu propre à la page. */
export type Loaded<T> = PageData<T> & T;

interface Props<T> {
  title: string;
  intro: string;
  state: PageState<T>;
  /** Contenu de la page, une fois les données chargées et non vides. */
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
      <header className="page-header">
        <h1>{title}</h1>
        <p>{intro}</p>
      </header>
      <FilterBar loading={state.status === "loading"} />
      {body}
      <footer className="footer">
        Données : Olist, « Brazilian E-Commerce Public Dataset » (Kaggle, licence CC BY-NC-SA 4.0).
      </footer>
    </div>
  );
}

export function Notice({ children, kind }: { children: ReactNode; kind?: "error" }) {
  return (
    <div className="notice section" data-kind={kind} role={kind === "error" ? "alert" : "status"}>
      {children}
    </div>
  );
}

/** « vs 04/07/2017 – 31/12/2017 » si une période de comparaison existe. */
export function deltaNote(data: PageData<unknown>): string | null {
  const previous = data.period.previous;
  return previous ? `vs ${dateLabel(previous.start)} – ${dateLabel(previous.end)}` : null;
}

export function NoComparison({ data }: { data: PageData<unknown> }) {
  if (data.period.previous) return null;
  return (
    <p className="caption">
      Pas de comparaison : la période précédente sortirait de la plage de données représentative (dès janvier 2017).
    </p>
  );
}

export function Section({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <section className="section">
      {title && <h2>{title}</h2>}
      {children}
    </section>
  );
}
