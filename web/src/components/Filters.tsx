// Sélecteurs de l'en-tête : période d'achat (avec raccourcis) et États du client.
import { CalendarDays, ChevronDown, MapPin } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { useFilters, useMeta } from "../lib/data";
import { longDate } from "../lib/format";

/** Bouton-pilule qui ouvre un panneau ; se ferme au clic extérieur ou avec Échap. */
function PopoverPill({ icon, label, children, title }: { icon: ReactNode; label: string; title: string; children: ReactNode }) {
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

  return (
    <div className="popover-anchor" ref={root}>
      <button type="button" className="pill" aria-haspopup="dialog" aria-expanded={open} onClick={() => setOpen(!open)}>
        {icon}
        <span>{label}</span>
        <ChevronDown size={16} aria-hidden="true" />
      </button>
      {open && (
        <div className="popover" role="dialog" aria-label={title}>
          {children}
        </div>
      )}
    </div>
  );
}

export function PeriodFilter() {
  const meta = useMeta();
  const { filters, setFilters } = useFilters();
  const presets = [
    { label: "Période représentative", start: meta.default_start, end: meta.default_end },
    { label: "2017", start: "2017-01-01", end: "2017-12-31" },
    { label: "2018 (janv.–août)", start: "2018-01-01", end: "2018-08-31" },
    { label: "6 derniers mois", start: "2018-03-01", end: "2018-08-31" },
    { label: "Toutes les données", start: meta.min_date, end: meta.max_date },
  ];
  const label = `${longDate(filters.start)}  →  ${longDate(filters.end)}`;

  return (
    <PopoverPill icon={<CalendarDays size={18} aria-hidden="true" />} label={label} title="Période d'achat">
      <h3>Période d'achat</h3>
      <div className="presets">
        {presets.map((p) => (
          <button
            key={p.label}
            type="button"
            className="chip"
            aria-pressed={filters.start === p.start && filters.end === p.end}
            onClick={() => setFilters({ ...filters, start: p.start, end: p.end })}
          >
            {p.label}
          </button>
        ))}
      </div>
      <div className="date-fields">
        <label>
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
        <label>
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
      <p className="popover-note">
        Avant janvier 2017 et après août 2018, les données ne comptent que quelques centaines de commandes.
      </p>
    </PopoverPill>
  );
}

export function StatesFilter() {
  const meta = useMeta();
  const { filters, setFilters } = useFilters();
  const selected = filters.states;
  const label =
    selected.length === 0 ? "Tous les États" : selected.length <= 3 ? selected.join(", ") : `${selected.length} États`;
  const toggle = (state: string) =>
    setFilters({
      ...filters,
      states: selected.includes(state) ? selected.filter((s) => s !== state) : [...selected, state],
    });

  return (
    <PopoverPill icon={<MapPin size={18} aria-hidden="true" />} label={label} title="États du client">
      <h3>États du client</h3>
      <div className="state-grid">
        {meta.states.map((state) => (
          <label key={state}>
            <input type="checkbox" checked={selected.includes(state)} onChange={() => toggle(state)} />
            {state}
          </label>
        ))}
      </div>
      <div className="popover-footer">
        <button type="button" className="link-button" onClick={() => setFilters({ ...filters, states: [] })}>
          Tous les États
        </button>
      </div>
    </PopoverPill>
  );
}
