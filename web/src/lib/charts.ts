// Options ECharts des graphiques du dashboard, sur le modèle de olist_dashboard/charts.py :
// une teinte par série, marques fines, grille discrète, étiquettes sélectives.
import type { ChartOption } from "../components/Chart";
import { shortMonth } from "./format";
import type { Tokens } from "./theme";

interface TooltipParam {
  dataIndex: number;
  seriesIndex?: number;
}

const escape = (text: string) =>
  text.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]!);

/** Info-bulle : titre en gras puis une ligne par élément. */
export const tooltipHtml = (title: string, lines: string[]) =>
  `<b>${escape(title)}</b>${lines.map((line) => `<br/>${escape(line)}`).join("")}`;

function base(t: Tokens) {
  return {
    animationDuration: 300,
    textStyle: { fontFamily: t.font, color: t.text2 },
    tooltip: {
      confine: true,
      backgroundColor: t.surface,
      borderColor: t.grid,
      borderWidth: 1,
      padding: [8, 10],
      textStyle: { color: t.text, fontSize: 12, fontFamily: t.font },
      extraCssText: "border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,.16);",
    },
  };
}

const axisLabel = (t: Tokens) => ({ color: t.muted, fontSize: 12 });

// --- Barres horizontales ------------------------------------------------------

export interface BarRow {
  label: string;
  value: number | null;
  /** Texte affiché au bout de la barre. */
  text: string;
  tooltip: string[];
}

/** Hauteur adaptée au nombre de barres (~30 px chacune : des barres fines). */
export const barHeight = (rows: number) => Math.max(110, rows * 30 + 16);

/** Barres horizontales d'une seule couleur, dans l'ordre des lignes (première en haut). */
export function barChart(rows: BarRow[], t: Tokens): ChartOption {
  const b = base(t);
  return {
    ...b,
    grid: { left: 4, right: 72, top: 4, bottom: 4, containLabel: true },
    xAxis: { type: "value", show: false, max: (v: { max: number }) => v.max * 1.1 || 1 },
    yAxis: {
      type: "category",
      inverse: true,
      data: rows.map((r) => r.label),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: t.baseline } },
      axisLabel: { color: t.text2, fontSize: 12 },
    },
    tooltip: {
      ...b.tooltip,
      trigger: "item",
      formatter: (p: TooltipParam) => tooltipHtml(rows[p.dataIndex].label, rows[p.dataIndex].tooltip),
    },
    series: [
      {
        type: "bar",
        data: rows.map((r) => r.value),
        barMaxWidth: 18,
        itemStyle: { color: t.accent, borderRadius: [0, 4, 4, 0] },
        emphasis: { itemStyle: { color: t.accent } },
        label: {
          show: true,
          position: "right",
          color: t.text2,
          fontSize: 12,
          formatter: (p: TooltipParam) => rows[p.dataIndex].text,
        },
      },
    ],
  };
}

// --- Évolution mensuelle --------------------------------------------------------

interface TrendInput {
  months: string[];
  values: number[];
  tooltip: (index: number) => string;
  yFormat: (value: number) => string;
  /** false : l'axe s'adapte aux valeurs (sans aire), pour une note entre 3,8 et 4,3. */
  zeroBased?: boolean;
}

/** Une série mensuelle en ligne (et aire légère si l'axe part de zéro), avec réticule. */
export function trendChart({ months, values, tooltip, yFormat, zeroBased = true }: TrendInput, t: Tokens): ChartOption {
  const b = base(t);
  return {
    ...b,
    grid: { left: 4, right: 16, top: 12, bottom: 4, containLabel: true },
    xAxis: {
      type: "category",
      data: months.map(shortMonth),
      boundaryGap: false,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: t.baseline } },
      axisLabel: { ...axisLabel(t), hideOverlap: true },
    },
    yAxis: {
      type: "value",
      scale: !zeroBased,
      splitLine: { lineStyle: { color: t.grid } },
      axisLabel: { ...axisLabel(t), formatter: yFormat },
    },
    tooltip: {
      ...b.tooltip,
      trigger: "axis",
      axisPointer: { type: "line", lineStyle: { color: t.baseline } },
      formatter: (params: TooltipParam[]) => tooltip(params[0].dataIndex),
    },
    series: [
      {
        type: "line",
        data: values,
        symbol: "circle",
        symbolSize: 8,
        lineStyle: { width: 2, color: t.accent },
        itemStyle: { color: t.accent, borderColor: t.surface, borderWidth: 2 },
        areaStyle: zeroBased ? { color: t.accentWash } : undefined,
      },
    ],
  };
}

// --- Colonnes empilées ---------------------------------------------------------

/** Colonnes empilées par mois, 3 séries au plus (couleurs catégorielles validées). */
export function stackedChart(
  months: string[], series: { name: string; values: number[] }[], unit: string, t: Tokens,
): ChartOption {
  const b = base(t);
  return {
    ...b,
    color: t.series,
    legend: { top: 0, left: 0, icon: "roundRect", itemWidth: 10, itemHeight: 10, textStyle: { color: t.text2 } },
    grid: { left: 4, right: 8, top: 36, bottom: 4, containLabel: true },
    xAxis: {
      type: "category",
      data: months.map(shortMonth),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: t.baseline } },
      axisLabel: { ...axisLabel(t), hideOverlap: true },
    },
    yAxis: {
      type: "value",
      splitLine: { lineStyle: { color: t.grid } },
      axisLabel: { ...axisLabel(t), formatter: (v: number) => `${v} ${unit}` },
    },
    tooltip: {
      ...b.tooltip,
      trigger: "axis",
      axisPointer: { type: "shadow", shadowStyle: { color: t.accentWash } },
      formatter: (params: TooltipParam[]) => {
        const i = params[0].dataIndex;
        const lines = series.map((s) => `${s.name} : ${s.values[i].toFixed(1).replace(".", ",")} ${unit}`);
        return tooltipHtml(shortMonth(months[i]), lines);
      },
    },
    series: series.map((s) => ({
      type: "bar",
      name: s.name,
      stack: "total",
      data: s.values,
      barMaxWidth: 24,
      // Le contour couleur du fond crée l'espace entre les segments.
      itemStyle: { borderColor: t.surface, borderWidth: 1 },
    })),
  };
}

// --- Nuage de points --------------------------------------------------------------

export interface ScatterPoint {
  x: number;
  y: number;
  name: string;
  tooltip: string[];
}

interface ScatterInput {
  points: ScatterPoint[];
  /** Nombre de points (les premiers) qui reçoivent une étiquette. */
  labeled: number;
  reference?: { value: number; label: string } | null;
  xName: string;
  yName: string;
  xFormat: (v: number) => string;
  yFormat: (v: number) => string;
}

/** Nuage d'une seule série ; étiquettes de part et d'autre de la ligne de repère. */
export function scatterChart(input: ScatterInput, t: Tokens): ChartOption {
  const { points, labeled, reference, xName, yName, xFormat, yFormat } = input;
  const b = base(t);
  const nameStyle = { color: t.muted, fontSize: 12 };
  return {
    ...b,
    grid: { left: 8, right: 24, top: 24, bottom: 8, containLabel: true },
    xAxis: {
      type: "value",
      name: xName,
      nameLocation: "middle",
      nameGap: 28,
      nameTextStyle: nameStyle,
      min: 0,
      splitLine: { show: false },
      axisLine: { lineStyle: { color: t.baseline } },
      axisLabel: { ...axisLabel(t), formatter: xFormat },
    },
    yAxis: {
      type: "value",
      name: yName,
      nameTextStyle: nameStyle,
      scale: true,
      splitLine: { lineStyle: { color: t.grid } },
      axisLabel: { ...axisLabel(t), formatter: yFormat },
    },
    tooltip: {
      ...b.tooltip,
      trigger: "item",
      formatter: (p: TooltipParam) =>
        p.seriesIndex === 0 ? tooltipHtml(points[p.dataIndex].name, points[p.dataIndex].tooltip) : "",
    },
    series: [
      {
        type: "scatter",
        symbolSize: 11,
        // Écarte verticalement les étiquettes qui se chevauchent.
        labelLayout: { moveOverlap: "shiftY" },
        itemStyle: { color: t.accent, borderColor: t.surface, borderWidth: 2 },
        data: points.map((p, i) => ({
          value: [p.x, p.y],
          label: {
            show: i < labeled,
            formatter: p.name,
            // Au-dessus des points mieux notés que la moyenne, en dessous des autres.
            position: (reference ? p.y >= reference.value : i % 2 === 0) ? "top" : "bottom",
            color: t.text2,
            fontSize: 12,
          },
        })),
        markLine: reference
          ? {
              silent: true,
              symbol: "none",
              lineStyle: { color: t.baseline, type: "solid", width: 1 },
              label: { formatter: reference.label, position: "insideStartBottom", color: t.muted, fontSize: 12 },
              data: [{ yAxis: reference.value }],
            }
          : undefined,
      },
    ],
  };
}

// --- Carte de chaleur ---------------------------------------------------------------

/** Lignes (jours) x colonnes (heures) sur la rampe séquentielle bleue. */
export function heatmapChart(
  rows: string[], columns: string[], values: number[][], unitName: string, t: Tokens,
): ChartOption {
  const b = base(t);
  const data = values.flatMap((row, y) => row.map((value, x) => [x, y, value]));
  const max = Math.max(1, ...data.map((d) => d[2]));
  return {
    ...b,
    grid: { left: 4, right: 72, top: 4, bottom: 4, containLabel: true },
    xAxis: {
      type: "category",
      data: columns,
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { ...axisLabel(t), interval: 2 },
    },
    yAxis: {
      type: "category",
      data: rows,
      inverse: true,
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: t.text2, fontSize: 12 },
    },
    visualMap: {
      min: 0,
      max,
      calculable: false,
      orient: "vertical",
      right: 0,
      top: "middle",
      itemWidth: 10,
      itemHeight: 120,
      text: [String(max), "0"],
      textStyle: { color: t.muted, fontSize: 11 },
      inRange: { color: t.sequential },
    },
    tooltip: {
      ...b.tooltip,
      trigger: "item",
      formatter: (p: TooltipParam & { value: number[] }) =>
        tooltipHtml(`${rows[p.value[1]]}, ${columns[p.value[0]]}`, [`${p.value[2].toLocaleString("fr-FR")} ${unitName}`]),
    },
    series: [{ type: "heatmap", data, itemStyle: { borderColor: t.surface, borderWidth: 2, borderRadius: 2 } }],
  };
}

// --- Concentration ------------------------------------------------------------------

/** Courbe de concentration (part cumulée du CA selon la part des vendeurs) et diagonale d'égalité. */
export function concentrationChart(
  curve: { seller_share: number; revenue_share: number }[],
  highlight: { x: number; y: number; label: string } | null,
  t: Tokens,
): ChartOption {
  const b = base(t);
  const pct = (v: number) => `${Math.round(v * 100)} %`;
  return {
    ...b,
    grid: { left: 8, right: 16, top: 32, bottom: 8, containLabel: true },
    xAxis: {
      type: "value", min: 0, max: 1, name: "Part des vendeurs", nameLocation: "middle", nameGap: 28,
      nameTextStyle: { color: t.muted, fontSize: 12 },
      splitLine: { show: false },
      axisLine: { lineStyle: { color: t.baseline } },
      axisLabel: { ...axisLabel(t), formatter: pct },
    },
    yAxis: {
      type: "value", min: 0, max: 1, name: "Part du CA", nameTextStyle: { color: t.muted, fontSize: 12 },
      splitLine: { lineStyle: { color: t.grid } },
      axisLabel: { ...axisLabel(t), formatter: pct },
    },
    tooltip: {
      ...b.tooltip,
      trigger: "axis",
      axisPointer: { type: "line", lineStyle: { color: t.baseline } },
      formatter: (params: TooltipParam[]) => {
        const p = curve[params.find((x) => x.seriesIndex === 0)?.dataIndex ?? 0];
        return `${pct(p.seller_share)} des vendeurs font ${pct(p.revenue_share)} du CA`;
      },
    },
    series: [
      {
        type: "line",
        data: curve.map((p) => [p.seller_share, p.revenue_share]),
        showSymbol: false,
        lineStyle: { width: 2, color: t.accent },
        areaStyle: { color: t.accentWash },
      },
      {
        type: "line",
        data: [[0, 0], [1, 1]],
        silent: true,
        showSymbol: false,
        lineStyle: { width: 1, color: t.baseline },
        endLabel: { show: true, formatter: "répartition égale", color: t.muted, fontSize: 11, offset: [-110, 14] },
      },
      ...(highlight
        ? [{
            type: "scatter",
            data: [[highlight.x, highlight.y]],
            silent: true,
            symbolSize: 10,
            itemStyle: { color: t.accent, borderColor: t.surface, borderWidth: 2 },
            label: { show: true, position: "right", formatter: highlight.label, color: t.text, fontSize: 12 },
          }]
        : []),
    ],
  };
}

// --- Carte des villes ---------------------------------------------------------------

export interface MapCity {
  name: string;
  lat: number;
  lng: number;
  size: number;
  tooltip: string[];
}

// Rectangle affiché (degrés) : le Brésil, à la même échelle sur les deux axes.
const LNG: [number, number] = [-75, -33];
const LAT: [number, number] = [-34, 6];
export const MAP_ASPECT = (LNG[1] - LNG[0]) / (LAT[1] - LAT[0]);

/**
 * Carte sans fond de carte (aucun téléchargement) : toutes les villes en points
 * gris dessinent le pays ; les ``highlighted`` premières sont des bulles dont la
 * surface est proportionnelle à ``size``.
 */
export function cityMapChart(cities: MapCity[], highlighted: number, t: Tokens): ChartOption {
  const b = base(t);
  const top = cities.slice(0, highlighted);
  const largest = Math.max(1, ...top.map((c) => c.size));
  const tooltipFor = (list: MapCity[]) => (p: TooltipParam) => tooltipHtml(list[p.dataIndex].name, list[p.dataIndex].tooltip);
  return {
    ...b,
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    xAxis: { type: "value", min: LNG[0], max: LNG[1], show: false },
    yAxis: { type: "value", min: LAT[0], max: LAT[1], show: false },
    tooltip: { ...b.tooltip, trigger: "item" },
    series: [
      {
        type: "scatter",
        data: cities.map((c) => [c.lng, c.lat]),
        symbolSize: 3,
        itemStyle: { color: t.baseline },
        tooltip: { formatter: tooltipFor(cities) },
        large: true,
        largeThreshold: 5000,
      },
      {
        type: "scatter",
        data: top.map((c) => [c.lng, c.lat]),
        symbolSize: (_: unknown, p: TooltipParam) => Math.max(4, Math.sqrt(top[p.dataIndex].size / largest) * 40),
        itemStyle: { color: t.accent, opacity: 0.6, borderColor: t.surface, borderWidth: 1 },
        tooltip: { formatter: tooltipFor(top) },
      },
    ],
  };
}
