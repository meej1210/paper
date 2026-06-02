<template>
  <div class="severity-tile-grid">
    <article
      v-for="tile in tiles"
      :key="tile.label"
      class="severity-tile"
      :class="[`severity-tile--${tile.tone}`, { 'severity-tile--zero': tile.count === 0 }]"
    >
      <span class="severity-tile__label">{{ tile.displayLabel }}</span>
      <strong class="severity-tile__count">{{ tile.count }}</strong>
      <span class="severity-tile__hint">{{ tile.hint }}</span>
    </article>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { severityLabel } from "../../utils/report-labels";

const DEFAULTS = [
  { label: "CRITICAL", tone: "critical", hint: "需要立即处置" },
  { label: "HIGH", tone: "high", hint: "24h 内处置" },
  { label: "MEDIUM", tone: "medium", hint: "纳入近期修复" },
  { label: "LOW", tone: "low", hint: "基线加固范畴" },
] as const;

const props = defineProps<{
  distribution: Record<string, number>;
  hints?: Partial<Record<string, string>>;
}>();

const tiles = computed(() =>
  DEFAULTS.map((d) => ({
    label: d.label,
    displayLabel: severityLabel(d.label),
    tone: d.tone,
    count: Number(props.distribution?.[d.label] || 0),
    hint: props.hints?.[d.label] ?? d.hint,
  }))
);
</script>

<style scoped>
.severity-tile-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}

@media (max-width: 900px) {
  .severity-tile-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.severity-tile {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 18px 20px;
  border-radius: 18px;
  background: var(--surface-0, #fff);
  border: 1px solid var(--line-soft, rgba(113, 143, 177, 0.24));
  border-left-width: 4px;
  box-shadow: var(--shadow-soft, 0 20px 45px rgba(15, 43, 74, 0.08));
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}

.severity-tile:hover {
  transform: translateY(-2px);
  box-shadow: 0 24px 50px rgba(15, 43, 74, 0.12);
}

.severity-tile__label {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: var(--ink-700, #49627d);
  text-transform: uppercase;
}

.severity-tile__count {
  font-size: 36px;
  font-weight: 800;
  line-height: 1;
  color: var(--ink-900, #132238);
}

.severity-tile__hint {
  font-size: 12px;
  color: var(--ink-700, #49627d);
}

.severity-tile--critical {
  border-left-color: #b42318;
}
.severity-tile--critical .severity-tile__label {
  color: #b42318;
}

.severity-tile--high {
  border-left-color: #ef4444;
}
.severity-tile--high .severity-tile__label {
  color: #b42318;
}

.severity-tile--medium {
  border-left-color: #d97706;
}
.severity-tile--medium .severity-tile__label {
  color: #b45309;
}

.severity-tile--low {
  border-left-color: #2563eb;
}
.severity-tile--low .severity-tile__label {
  color: #1d4ed8;
}

.severity-tile--zero {
  opacity: 0.55;
}

.severity-tile--zero .severity-tile__count {
  color: var(--ink-700, #49627d);
  font-weight: 700;
}
</style>
