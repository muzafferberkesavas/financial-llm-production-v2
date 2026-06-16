// Tree-shaken ECharts registration for the dashboard charts.
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { GaugeChart, PieChart, LineChart, BarChart, CustomChart } from "echarts/charts";
import { GridComponent, TooltipComponent, GraphicComponent } from "echarts/components";

use([
  CanvasRenderer,
  GaugeChart,
  PieChart,
  LineChart,
  BarChart,
  CustomChart,
  GridComponent,
  TooltipComponent,
  GraphicComponent,
]);

// Shared palette (mirrors style.css @theme).
export const C = {
  bg: "#07090d",
  surface2: "#131a24",
  border: "#1f2835",
  text: "#e6edf3",
  muted: "#7d8aa0",
  accent: "#5b9dff",
  bull: "#34d399",
  bear: "#f43f5e",
  watch: "#f0b454",
};

export const MONO = "IBM Plex Mono, monospace";
