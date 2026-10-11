// Tuile d'indicateur : valeur, écart à la période précédente, courbe des 12 derniers mois.
import type { Delta } from "../lib/delta";
import { InfoTip } from "./InfoTip";

interface Props {
  label: string;
  value: string;
  delta?: Delta | null;
  /** Libellé de la période de comparaison (« vs 04/07/2017 – 31/12/2017 »). */
  deltaNote?: string | null;
  help?: string;
  trend?: number[];
}

const ARROWS = { up: "▲", down: "▼", flat: "■" } as const;

export function Kpi({ label, value, delta, deltaNote, help, trend }: Props) {
  return (
    <div className="kpi">
      <div className="kpi-label">
        {label}
        {help && <InfoTip text={help} />}
      </div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-foot">
        {delta ? (
          <span className="delta" data-tone={delta.tone}>
            <span aria-hidden="true">{ARROWS[delta.direction]}</span>
            <span>
              {delta.text}
              {deltaNote && <span className="delta-note">{deltaNote}</span>}
            </span>
          </span>
        ) : (
          <span />
        )}
        {trend && trend.length > 1 && <Sparkline values={trend} />}
      </div>
    </div>
  );
}

function Sparkline({ values }: { values: number[] }) {
  const width = 96;
  const height = 32;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const points = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * (width - 4) + 2;
      const y = height - 2 - ((v - min) / span) * (height - 4);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const last = points.split(" ").at(-1)!.split(",");
  return (
    <svg className="sparkline" width={width} height={height} aria-hidden="true">
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <circle cx={last[0]} cy={last[1]} r="2.5" fill="var(--accent)" />
    </svg>
  );
}

export function KpiGrid({ children }: { children: React.ReactNode }) {
  return <div className="kpis">{children}</div>;
}
