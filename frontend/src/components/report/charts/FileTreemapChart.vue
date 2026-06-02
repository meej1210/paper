<template>
  <div ref="chartEl" class="echart-canvas file-treemap-chart"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from "vue";
import { echarts, REPORT_COLORS } from "../../../utils/echarts-core";
import type { ECharts } from "../../../utils/echarts-core";
import { displayFileName } from "../../../utils/report-labels";

const props = defineProps<{
  data: Array<{ label: string; count: number }>;
}>();

const chartEl = ref<HTMLDivElement | null>(null);
let instance: ECharts | null = null;
let resizeObserver: ResizeObserver | null = null;

function buildOption() {
  const items = props.data || [];
  return {
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(15, 23, 42, 0.92)",
      borderColor: "transparent",
      textStyle: { color: "#fff", fontSize: 12 },
      formatter: (p: any) => {
        const fullPath = p.data?.fullPath || p.name;
        return `<strong>${displayFileName(fullPath)}</strong><br/><span style="color:rgba(255,255,255,0.7)">${fullPath}</span><br/>问题数：${p.value}`;
      },
    },
    series: [
      {
        type: "treemap",
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        label: {
          show: true,
          formatter: (params: any) => displayFileName(params.data?.fullPath || params.name),
          color: "#fff",
          fontSize: 11,
          fontWeight: 600,
          overflow: "truncate",
          ellipsis: "...",
        },
        upperLabel: { show: false },
        itemStyle: {
          borderColor: "#fff",
          borderWidth: 2,
          gapWidth: 2,
        },
        levels: [
          {
            itemStyle: {
              borderColor: "#fff",
              borderWidth: 2,
              gapWidth: 2,
            },
          },
        ],
        data: items.map((i) => ({
          name: displayFileName(i.label),
          fullPath: i.label,
          value: i.count,
          itemStyle: { color: buildBlockColor(i.count, items) },
        })),
      },
    ],
  };
}

function buildBlockColor(value: number, items: Array<{ count: number }>) {
  const max = Math.max(...items.map((i) => i.count), 1);
  const ratio = value / max;
  if (ratio > 0.7) return REPORT_COLORS.critical;
  if (ratio > 0.4) return REPORT_COLORS.high;
  if (ratio > 0.2) return REPORT_COLORS.medium;
  return REPORT_COLORS.accent;
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

watch(() => props.data, () => render(), { deep: true });

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
  height: 280px;
}
</style>
