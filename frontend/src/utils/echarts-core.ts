import * as echarts from "echarts/core";
import { RadarChart, PieChart, TreemapChart } from "echarts/charts";
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GraphicComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  RadarChart,
  PieChart,
  TreemapChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GraphicComponent,
  CanvasRenderer,
]);

export { echarts };
export type { ECharts } from "echarts/core";

export const REPORT_COLORS = {
  critical: "#b42318",
  high: "#ef4444",
  medium: "#d97706",
  low: "#2563eb",
  info: "#94a3b8",
  unknown: "#94a3b8",
  accent: "#17a2ad",
  ink900: "#132238",
  ink700: "#49627d",
} as const;

export function severityColor(label?: string): string {
  if (!label) return REPORT_COLORS.unknown;
  const v = label.toUpperCase();
  if (v.includes("CRITICAL")) return REPORT_COLORS.critical;
  if (v.includes("HIGH")) return REPORT_COLORS.high;
  if (v.includes("MEDIUM")) return REPORT_COLORS.medium;
  if (v.includes("LOW")) return REPORT_COLORS.low;
  if (v.includes("INFO")) return REPORT_COLORS.info;
  return REPORT_COLORS.unknown;
}
