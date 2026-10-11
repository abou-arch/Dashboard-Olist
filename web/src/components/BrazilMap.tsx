// Carte des États du Brésil (tracés @svg-maps/brazil, CC BY 4.0) colorée selon une valeur.
import brazil from "@svg-maps/brazil";
import { useState } from "react";

import type { Tokens } from "../lib/theme";

/** Nom complet des États, d'après la carte : « sp » -> « São Paulo ». */
export const STATE_NAMES: Record<string, string> = Object.fromEntries(
  brazil.locations.map((l) => [l.id.toUpperCase(), l.name]),
);

interface Props {
  /** Valeur par sigle d'État (SP, RJ…) ; les États absents restent gris. */
  values: Record<string, number>;
  tooltip: (state: string) => string[];
  t: Tokens;
  label: string;
}

export function BrazilMap({ values, tooltip, t, label }: Props) {
  const [hover, setHover] = useState<{ state: string; x: number; y: number } | null>(null);
  // Teinte selon le rang (classes de même effectif) : São Paulo pèse près de 40 % du
  // CA, une échelle proportionnelle rendrait tous les autres États identiques.
  const ranked = Object.entries(values)
    .filter(([, value]) => value > 0)
    .sort((a, b) => a[1] - b[1])
    .map(([state]) => state);
  const classes = t.sequential.length - 1;
  const color = (state: string) => {
    const rank = ranked.indexOf(state);
    if (rank < 0) return t.sequential[0];
    return t.sequential[1 + Math.min(classes - 1, Math.floor((rank / ranked.length) * classes))];
  };

  return (
    <div style={{ position: "relative" }}>
      <svg className="brazil-map" viewBox={brazil.viewBox} role="img" aria-label={label}>
        {brazil.locations.map((location) => {
          const state = location.id.toUpperCase();
          return (
            <path
              key={state}
              d={location.path}
              fill={color(state)}
              onMouseMove={(e) => {
                const box = (e.currentTarget.ownerSVGElement!.parentElement as HTMLElement).getBoundingClientRect();
                setHover({ state, x: e.clientX - box.left, y: e.clientY - box.top });
              }}
              onMouseLeave={() => setHover(null)}
            />
          );
        })}
      </svg>
      {hover && (
        <div
          className="map-tooltip"
          style={{ left: hover.x + 12, top: hover.y + 12 }}
          aria-hidden="true"
        >
          <strong>{STATE_NAMES[hover.state]}</strong>
          {tooltip(hover.state).map((line) => (
            <div key={line}>{line}</div>
          ))}
        </div>
      )}
    </div>
  );
}
