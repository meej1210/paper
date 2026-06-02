<template>
  <div ref="chartEl" class="echart-canvas owasp-radar-chart"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from "vue";
import { echarts, REPORT_COLORS } from "../../../utils/echarts-core";
import type { ECharts } from "../../../utils/echarts-core";
import { owaspLabel } from "../../../utils/report-labels";

const props = defineProps<{
  data: Array<{ label: string; count: number }>;
  variant?: "danger" | "neutral";
}>();

const chartEl = ref<HTMLDivElement | null>(null);
let instance: ECharts | null = null;
let resizeObserver: ResizeObserver | null = null;

function colorByVariant() {
  return props.variant === "neutral" ? REPORT_COLORS.accent : REPORT_COLORS.critical;
}

function buildOption() {
  const items = props.data || [];
  const max = Math.max(...items.map((i) => i.count), 1);
  const main = colorByVariant();
  return {
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(15, 23, 42, 0.92)",
      borderColor: "transparent",
      textStyle: { color: "#fff", fontSize: 12 },
      formatter: (params: any) => {
        const values: number[] = params.value || [];
        const lines = items.map((i, idx) => `${owaspLabel(i.label)}：<strong>${values[idx] ?? 0}</strong>`);
        return lines.join("<br/>");
      },
    },
    radar: {
      center: ["50%", "54%"],
      radius: "65%",
      indicator: items.map((i) => ({ name: owaspLabel(i.label), max })),
      axisName: {
        color: REPORT_COLORS.ink700,
        fontSize: 11,
        backgroundColor: "rgba(255,255,255,0.6)",
        borderRadius: 4,
        padding: [2, 6],
      },
      splitArea: {
        areaStyle: {
          color: ["rgba(180,35,24,0.04)", "rgba(180,35,24,0.08)"],
          shadowColor: "rgba(0,0,0,0.05)",
          shadowBlur: 8,
        },
      },
      splitLine: { lineStyle: { color: "rgba(113,143,177,0.24)" } },
      axisLine: { lineStyle: { color: "rgba(113,143,177,0.24)" } },
    },
    series: [
      {
        type: "radar",
        symbol: "circle",
        symbolSize: 6,
        data: [
          {
            value: items.map((i) => i.count),
            name: "本次扫描",
            areaStyle: { color: main + "4d" },
            lineStyle: { color: main, width: 2 },
            itemStyle: { color: main },
          },
        ],
      },
    ],
  };
}

function render() {
  if (!instance) return;
  instance.setOption(buildOption(), true);
}

onMounted(() => {
  if (!chartEl.value) return;
  instance = echarts.init(chartEl.value);
  render();
  resizeObserver = new ResizeObserver(() => instance?.resize());
  resizeObserver.observe(chartEl.value);
});

watch(
  () => [props.data, props.variant],
  () => render(),
  { deep: true }
);

onUnmounted(() => {
  resizeObserver?.disconnect();
  resizeObserver = null;
  instance?.dispose();
  instance = null;
});
</script>

<style scoped>
.echart-canvas {
  width: 100%;
  height: 320px;
}
</style>
