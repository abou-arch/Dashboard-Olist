// Métadonnées (bornes, États), filtres portés par l'adresse de la page, et
// chargement des données de chaque page.
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router";

import { fetchMeta, fetchPage, type Filters, type Meta, type PageData, type PageName } from "./api";

const MetaContext = createContext<Meta | null>(null);

type Load<T> = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; data: T };

/** Charge les métadonnées une fois, puis affiche l'application. */
export function MetaProvider({ children }: { children: (meta: Load<Meta>) => ReactNode }) {
  const [state, setState] = useState<Load<Meta>>({ status: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    fetchMeta(controller.signal)
      .then((data) => setState({ status: "ready", data }))
      .catch((error: Error) => {
        if (error.name !== "AbortError") setState({ status: "error", message: error.message });
      });
    return () => controller.abort();
  }, []);
  return (
    <MetaContext.Provider value={state.status === "ready" ? state.data : null}>
      {children(state)}
    </MetaContext.Provider>
  );
}

export function useMeta(): Meta {
  const meta = useContext(MetaContext);
  if (!meta) throw new Error("Métadonnées pas encore chargées.");
  return meta;
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

/**
 * Filtres lus dans l'adresse (?du=…&au=…&etats=SP,RJ), pour qu'une vue se
 * partage par un simple lien ; les valeurs par défaut n'y figurent pas.
 */
export function useFilters() {
  const meta = useMeta();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const filters: Filters = useMemo(() => {
    const date = (key: string, fallback: string) => {
      const value = params.get(key) ?? "";
      return ISO_DATE.test(value) ? value : fallback;
    };
    const states = (params.get("etats") ?? "")
      .split(",")
      .map((s) => s.trim().toUpperCase())
      .filter((s) => meta.states.includes(s));
    return {
      start: date("du", meta.default_start),
      end: date("au", meta.default_end),
      states: [...new Set(states)].sort(),
    };
  }, [params, meta]);

  const setFilters = (next: Filters) => {
    const out = new URLSearchParams();
    if (next.start !== meta.default_start) out.set("du", next.start);
    if (next.end !== meta.default_end) out.set("au", next.end);
    if (next.states.length) out.set("etats", [...next.states].sort().join(","));
    // Virgules laissées lisibles dans l'adresse : ?etats=RJ,SP plutôt que RJ%2CSP.
    const search = out.toString().replace(/%2C/g, ",");
    navigate({ pathname, search: search ? `?${search}` : "" }, { replace: true });
  };

  const isDefault =
    filters.start === meta.default_start && filters.end === meta.default_end && !filters.states.length;
  return { filters, setFilters, isDefault, search: params.toString() };
}

export type PageState<T> =
  | { status: "loading"; data?: PageData<T> }
  | { status: "error"; message: string; data?: PageData<T> }
  | { status: "ready"; data: PageData<T> };

/** Données d'une page pour les filtres courants ; garde l'affichage précédent pendant un rechargement. */
export function usePageData<T>(page: PageName, filters: Filters): PageState<T> {
  const [state, setState] = useState<PageState<T>>({ status: "loading" });
  const key = `${page}|${filters.start}|${filters.end}|${filters.states.join(",")}`;

  useEffect(() => {
    if (filters.start > filters.end) {
      setState({ status: "error", message: "La date de début doit précéder la date de fin." });
      return;
    }
    const controller = new AbortController();
    setState((previous) => ({ status: "loading", data: previous.data }));
    fetchPage<T>(page, filters, controller.signal)
      .then((data) => setState({ status: "ready", data }))
      .catch((error: Error) => {
        if (error.name !== "AbortError") {
          const message = `Impossible de charger les données : ${error.message}`;
          setState((previous) => ({ status: "error", message, data: previous.data }));
        }
      });
    return () => controller.abort();
    // La clé résume page et filtres : inutile de relancer pour un nouvel objet identique.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return state;
}
