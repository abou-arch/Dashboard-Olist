// Tuile d'indicateur (maquette) : titre, écart, icône, valeur, petite courbe ou barres.
import { ArrowDownRight, ArrowRight, ArrowUpRight, type LucideIcon } from "lucide-react";

import { useId } from "react";

import type { Delta } from "../lib/delta";

interface Props {
  label: string;
  value: React.ReactNode;
  icon: LucideIcon;
  delta?: Delta | null;
  /** Texte sous la valeur ; par défaut, la période de comparaison. */
  note?: string | null;
  help?: string;
  trend?: number[];
  trendKind?: "area" | "bars";
}

const ARROWS = { up: ArrowUpRight, down: ArrowDownRight, flat: ArrowRight };

export function Kpi({ label, value, icon: Icon, delta, note, help, trend, trendKind = "area" }: Props) {
  const Arrow = delta ? ARROWS[delta.direction] : null;
  return (
    <div className="kpi" title={help}>
      <div className="kpi-title">
        <span>{label}</span>
        {delta && Arrow && (
          <span className="delta" data-tone={delta.tone}>
            <Arrow size={15} aria-hidden="true" />
            {delta.text}
          </span>
        )}
      </div>
      <span className="kpi-icon" aria-hidden="true">
        <Icon size={22} strokeWidth={1.8} />
      </span>
      <div className="kpi-value">{value}</div>
      <div className="kpi-foot">
        <span className="kpi-note">{note}</span>
        {trend && trend.length > 1 && (trendKind === "bars" ? <SparkBars values={trend} /> : <SparkArea values={trend} />)}
      </div>
    </div>
  );
}

const WIDTH = 150;
const HEIGHT = 50;

function scale(values: number[]) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return (v: number) => HEIGHT - 3 - ((v - min) / span) * (HEIGHT - 8);
}

function SparkArea({ values }: { values: number[] }) {
  const y = scale(values);
  const points = values.map((v, i) => [(i / (values.length - 1)) * WIDTH, y(v)] as const);
  const line = points.map(([x, py]) => `${x.toFixed(1)},${py.toFixed(1)}`).join(" ");
  const id = `spark${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  return (
    <svg className="spark" width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.35" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,${HEIGHT} ${line} ${WIDTH},${HEIGHT}`} fill={`url(#${id})`} />
      <polyline points={line} fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

function SparkBars({ values }: { values: number[] }) {
  const y = scale(values);
  const step = WIDTH / values.length;
  return (
    <svg className="spark" width={WIDTH} height={HEIGHT} viewBox={`0 0 ${WIDTH} ${HEIGHT}`} aria-hidden="true">
      {values.map((v, i) => (
        <rect
          key={i}
          x={i * step + 1}
          y={y(v)}
          width={Math.max(2, step - 3)}
          height={HEIGHT - y(v)}
          rx="1.5"
          fill="currentColor"
          opacity={i === values.length - 1 ? 1 : 0.55}
        />
      ))}
    </svg>
  );
}
