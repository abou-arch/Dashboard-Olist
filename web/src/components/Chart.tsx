// Graphique ECharts : s'adapte à la largeur de son conteneur.
import { BarChart, HeatmapChart, LineChart, ScatterChart } from "echarts/charts";
import {
  GridComponent, LegendComponent, MarkLineComponent, TooltipComponent, VisualMapComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";

echarts.use([
  BarChart, HeatmapChart, LineChart, ScatterChart,
  GridComponent, LegendComponent, MarkLineComponent, TooltipComponent, VisualMapComponent,
  CanvasRenderer,
]);

export type ChartOption = echarts.EChartsCoreOption;

interface Props {
  option: ChartOption;
  /** Hauteur en pixels, ou proportion largeur / hauteur (``aspect``). */
  height?: number;
  aspect?: number;
  /** Description du graphique pour les lecteurs d'écran. */
  label: string;
}

export function Chart({ option, height = 320, aspect, label }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const instance = echarts.init(ref.current, null, { renderer: "canvas" });
    chart.current = instance;
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      instance.dispose();
      chart.current = null;
    };
  }, []);

  useEffect(() => {
    chart.current?.setOption(option, { notMerge: true });
  }, [option]);

  const style = aspect ? { aspectRatio: String(aspect) } : { height };
  return <div ref={ref} className="chart" style={style} role="img" aria-label={label} />;
}
