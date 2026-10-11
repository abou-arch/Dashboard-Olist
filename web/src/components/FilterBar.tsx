// Filtres de la période d'achat et des États du client, communs à toutes les pages.
import { useEffect, useRef, useState } from "react";

import { useFilters, useMeta } from "../lib/data";
import { InfoTip } from "./InfoTip";

export function FilterBar({ loading }: { loading: boolean }) {
  const meta = useMeta();
  const { filters, setFilters, isDefault } = useFilters();

  return (
    <div className="filters">
      <div className="field-pair">
        <label className="field">
          Du
          <input
            type="date"
            value={filters.start}
            min={meta.min_date}
            max={meta.max_date}
            required
            onChange={(e) => e.target.value && setFilters({ ...filters, start: e.target.value })}
          />
        </label>
        <label className="field">
          Au
          <input
            type="date"
            value={filters.end}
            min={meta.min_date}
            max={meta.max_date}
            required
            onChange={(e) => e.target.value && setFilters({ ...filters, end: e.target.value })}
          />
        </label>
      </div>
      <StateSelect
        all={meta.states}
        selected={filters.states}
        onChange={(states) => setFilters({ ...filters, states })}
      />
      <InfoTip text="Par défaut, janvier 2017 à août 2018 : les mois en dehors de cette plage ne comptent que quelques centaines de commandes." />
      {!isDefault && (
        <button
          type="button"
          className="link-button"
          onClick={() => setFilters({ start: meta.default_start, end: meta.default_end, states: [] })}
        >
          Réinitialiser
        </button>
      )}
      {loading && <div className="loading-bar" role="progressbar" aria-label="Chargement" />}
    </div>
  );
}

interface StateSelectProps {
  all: string[];
  selected: string[];
  onChange: (states: string[]) => void;
}

function StateSelect({ all, selected, onChange }: StateSelectProps) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent ? event.key === "Escape" : !root.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  const summary =
    selected.length === 0 ? "Tous les États" : selected.length <= 4 ? selected.join(", ") : `${selected.length} États`;
  const toggle = (state: string) =>
    onChange(selected.includes(state) ? selected.filter((s) => s !== state) : [...selected, state]);

  return (
    <div className="field state-select" ref={root}>
      États du client
      <button
        type="button"
        className="select-button"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <span>{summary}</span>
        <span aria-hidden="true">▾</span>
      </button>
      {open && (
        <div className="state-panel" role="group" aria-label="États du client">
          <div className="state-grid">
            {all.map((state) => (
              <label key={state}>
                <input type="checkbox" checked={selected.includes(state)} onChange={() => toggle(state)} />
                {state}
              </label>
            ))}
          </div>
          <div className="state-panel-footer">
            <button type="button" className="link-button" onClick={() => onChange([])}>
              Tous les États
            </button>
            <button type="button" className="link-button" onClick={() => setOpen(false)}>
              Fermer
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
