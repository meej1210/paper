<template>
  <div class="panel report-panel">
    <div class="report-section-head">
      <div>
        <h3>{{ title || 'AI 综合建议' }}</h3>
        <div class="muted">{{ description || '基于本次扫描结果生成的解读与处置路径。' }}</div>
      </div>
      <div class="report-tabs" v-if="tabs.length > 1">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          type="button"
          class="report-tabs__btn"
          :class="{ 'report-tabs__btn--active': activeKey === tab.key }"
          @click="activeKey = tab.key"
        >{{ tab.label }}</button>
      </div>
    </div>
    <div class="report-tab-panel" v-if="activeTab">
      <template v-if="activeTab.content.type === 'mixed'">
        <p
          v-if="activeTab.content.intro"
          class="report-summary report-summary--inline"
        >{{ activeTab.content.intro }}</p>
        <ul
          v-if="activeTab.content.items && activeTab.content.items.length"
          class="insight-list insight-list--tight"
        >
          <li v-for="item in activeTab.content.items" :key="item">{{ item }}</li>
        </ul>
      </template>
      <p
        v-else-if="activeTab.content.type === 'prose'"
        class="report-summary report-summary--inline"
      >{{ activeTab.content.text }}</p>
      <ul
        v-else-if="activeTab.content.type === 'list'"
        class="insight-list insight-list--tight"
      >
        <li v-for="item in activeTab.content.items" :key="item">{{ item }}</li>
      </ul>
      <ol
        v-else-if="activeTab.content.type === 'ordered'"
        class="priority-list"
      >
        <li
          v-for="(step, idx) in activeTab.content.items"
          :key="step.title"
          :class="{ 'priority-list__item--danger': dangerFirst(activeTab) && idx === 0 }"
        >
          <strong :class="{ 'text-danger': dangerFirst(activeTab) && idx === 0 }">{{ step.title }}</strong>
          <p>{{ step.detail }}</p>
        </li>
      </ol>
      <div v-else-if="activeTab.content.type === 'timeline'" class="report-timeline">
        <article
          class="timeline-step"
          v-for="step in activeTab.content.steps"
          :key="step.phase"
        >
          <div class="timeline-step__marker">{{ step.phase }}</div>
          <div class="timeline-step__body">
            <div class="timeline-step__title">{{ step.title }}</div>
            <p class="timeline-step__summary">{{ step.summary }}</p>
            <ul class="insight-list insight-list--tight">
              <li
                v-for="item in step.items"
                :key="`${step.phase}-${item}`"
              >{{ item }}</li>
            </ul>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

export type AdviceProseContent = { type: "prose"; text: string };
export type AdviceListContent = { type: "list"; items: string[] };
export type AdviceOrderedContent = {
  type: "ordered";
  items: Array<{ title: string; detail: string }>;
  dangerFirst?: boolean;
};
export type AdviceTimelineContent = {
  type: "timeline";
  steps: Array<{ phase: string; title: string; summary: string; items: string[] }>;
};
export type AdviceMixedContent = {
  type: "mixed";
  intro?: string;
  items?: string[];
};

export type AdviceContent =
  | AdviceProseContent
  | AdviceListContent
  | AdviceOrderedContent
  | AdviceTimelineContent
  | AdviceMixedContent;

export type AdviceTab = {
  key: string;
  label: string;
  content: AdviceContent;
};

const props = defineProps<{
  tabs: AdviceTab[];
  title?: string;
  description?: string;
  defaultTabKey?: string;
}>();

const activeKey = ref<string>(props.defaultTabKey || props.tabs[0]?.key || "");

watch(
  () => props.tabs,
  (next) => {
    if (!next.some((t) => t.key === activeKey.value)) {
      activeKey.value = props.defaultTabKey || next[0]?.key || "";
    }
  }
);

const activeTab = computed(() => props.tabs.find((t) => t.key === activeKey.value));

function dangerFirst(tab: AdviceTab) {
  if (tab.content.type !== "ordered") return false;
  return tab.content.dangerFirst !== false;
}
</script>

<style scoped>
.report-tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.report-tabs__btn {
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid var(--line-strong, rgba(56, 104, 153, 0.28));
  background: #fff;
  color: var(--ink-700, #49627d);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.16s ease;
}

.report-tabs__btn:hover {
  color: var(--ink-900, #132238);
  border-color: var(--accent-500, #17a2ad);
}

.report-tabs__btn--active {
  background: var(--accent-500, #17a2ad);
  border-color: var(--accent-500, #17a2ad);
  color: #fff;
}

.report-tab-panel {
  margin-top: 4px;
}

.report-summary--inline {
  margin: 0 0 12px;
  font-size: 14px;
  color: var(--ink-700, #49627d);
  font-weight: 600;
}
</style>
