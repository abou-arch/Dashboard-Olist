// Tableau triable (clic sur un en-tête).
import { useMemo, useState } from "react";

export interface Column<T> {
  key: keyof T & string;
  label: string;
  format?: (value: T[keyof T], row: T) => string;
  align?: "left" | "right";
}

interface Props<T> {
  rows: T[];
  columns: Column<T>[];
  caption: string;
  sortable?: boolean;
}

export function DataTable<T extends object>({ rows, columns, caption, sortable = true }: Props<T>) {
  const [sort, setSort] = useState<{ key: keyof T; desc: boolean } | null>(null);
  const sorted = useMemo(() => {
    if (!sort) return rows;
    return [...rows].sort((a, b) => {
      const x = a[sort.key] as unknown;
      const y = b[sort.key] as unknown;
      if (x == null) return 1;
      if (y == null) return -1;
      const order = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y), "fr");
      return sort.desc ? -order : order;
    });
  }, [rows, sort]);

  return (
    <div className="table-wrap">
      <table>
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((col) => {
              const active = sort?.key === col.key;
              return (
                <th
                  key={col.key}
                  data-align={col.align}
                  aria-sort={active ? (sort!.desc ? "descending" : "ascending") : undefined}
                >
                  {sortable ? (
                    <button
                      type="button"
                      onClick={() => setSort({ key: col.key, desc: active ? !sort!.desc : col.align === "right" })}
                    >
                      {col.label}
                      {active ? (sort!.desc ? " ↓" : " ↑") : ""}
                    </button>
                  ) : (
                    col.label
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr key={i}>
              {columns.map((col) => {
                const value = row[col.key];
                return (
                  <td key={col.key} data-align={col.align}>
                    {col.format ? col.format(value, row) : value == null ? "–" : String(value)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Tableau repliable sous un graphique (alternative accessible aux couleurs). */
export function DataDetails<T extends object>(props: Props<T> & { summary: string }) {
  return (
    <details className="data">
      <summary>{props.summary}</summary>
      <DataTable {...props} />
    </details>
  );
}
