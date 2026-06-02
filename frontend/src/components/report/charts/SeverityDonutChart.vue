<template>
  <div class="severity-donut-chart">
    <div ref="chartEl" class="echart-canvas severity-donut-chart__canvas"></div>
    <div class="severity-donut-chart__center">
      <strong>{{ total }}</strong>
      <span>{{ centerLabel || '总数' }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { echarts, severityColor } from "../../../utils/echarts-core";
import type { ECharts } from "../../../utils/echarts-core";
import { severityLabel } from "../../../utils/report-labels";

const props = defineProps<{
  data: Array<{ label: string; count: number }>;
  total?: number;
  centerLabel?: string;
}>();

const chartEl = ref<HTMLDivElement | null>(null);
let instance: ECharts | null = null;
let resizeObserver: ResizeObserver | null = null;

const total = computed(() => {
  if (typeof props.total === "number") return props.total;
  return (props.data || []).reduce((s, i) => s + (i.count || 0), 0);
});

function buildOption() {
  const items = (props.data || []).filter((i) => i.count > 0);
  return {
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(15, 23, 42, 0.92)",
      borderColor: "transparent",
      textStyle: { color: "#fff", fontSize: 12 },
      formatter: (p: any) =>
        `<strong>${p.name}</strong><br/>数量：${p.value}<br/>占比：${p.percent}%`,
    },
    series: [
      {
        name: "严重度分布",
        type: "pie",
        radius: ["62%", "82%"],
        center: ["50%", "50%"],
        avoidLabelOverlap: false,
        label: { show: false },
        labelLine: { show: false },
        emphasis: {
          scale: true,
          scaleSize: 4,
          itemStyle: { shadowBlur: 12, shadowColor: "rgba(0,0,0,0.12)" },
        },
        data: items.map((i) => ({
          name: severityLabel(i.label),
          value: i.count,
          itemStyle: { color: severityColor(i.label), borderColor: "#fff", borderWidth: 2 },
        })),
      },
    ],
  };
}

function render() {
  if (!instance) return;
  if ((props.data || []).every((i) => !i.count)) {
    instance.setOption(
      {
        series: [
          {
            type: "pie",
            radius: ["62%", "82%"],
            center: ["50%", "50%"],
            silent: true,
            label: { show: false },
            data: [{ value: 1, itemStyle: { color: "rgba(113,143,177,0.2)" } }],
          },
        ],
      },
      true
    );
    return;
  }
  instance.setOption(buildOption(), true);
}

onMounted(() => {
  if (!chartEl.value) return;
  instance = echarts.init(chartEl.value);
  render();
  resizeObserver = new ResizeObserver(() => instance?.resize());
  resizeObserver.observe(chartEl.value);
});

watch(() => [props.data, props.total, props.centerLabel], () => render(), { deep: true });

onUnmounted(() => {
  resizeObserver?.disconnect();
  resizeObserver = null;
  instance?.dispose();
  instance = null;
});
</script>

<style scoped>
.severity-donut-chart {
  position: relative;
  width: 100%;
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.echart-canvas {
  width: 100%;
  height: 100%;
}

.severity-donut-chart__center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  pointer-events: none;
}

.severity-donut-chart__center strong {
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
  color: var(--ink-900, #132238);
}

.severity-donut-chart__center span {
  font-size: 11px;
  color: var(--ink-700, #49627d);
  margin-top: 4px;
  letter-spacing: 0.04em;
}
</style>
