<template>
  <Transition name="issue-drawer-fade">
    <div v-if="open" class="issue-drawer-mask" @click.self="$emit('close')"></div>
  </Transition>
  <Transition name="issue-drawer-slide">
    <aside
      v-if="open"
      class="issue-drawer"
      role="dialog"
      aria-modal="true"
      :aria-label="title || '详情'"
    >
      <header class="issue-drawer__head">
        <div class="issue-drawer__head-main">
          <div class="issue-drawer__title-row">
            <span v-if="level" class="issue-badge" :class="severityToneClass(level)">{{ severityLabel(level) }}</span>
            <h3>{{ title || '详情' }}</h3>
          </div>
          <div v-if="subtitle" class="muted issue-drawer__subtitle">{{ subtitle }}</div>
        </div>
        <button
          class="issue-drawer__close"
          type="button"
          @click="$emit('close')"
          aria-label="关闭"
        >×</button>
      </header>
      <div class="issue-drawer__body">
        <slot />
      </div>
    </aside>
  </Transition>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, watch } from "vue";
import { severityLabel } from "../../utils/report-labels";

const props = defineProps<{
  open: boolean;
  level?: string;
  title?: string;
  subtitle?: string;
}>();

const emit = defineEmits<{ (e: "close"): void }>();

function severityToneClass(label?: string) {
  if (!label) return "";
  const value = label.toUpperCase();
  if (value.includes("CRITICAL") || value.includes("HIGH")) return "is-danger";
  if (value.includes("MEDIUM")) return "is-warning";
  if (value.includes("LOW")) return "is-info";
  return "";
}

function handleEsc(event: KeyboardEvent) {
  if (event.key === "Escape" && props.open) emit("close");
}

watch(
  () => props.open,
  (next) => {
    document.body.style.overflow = next ? "hidden" : "";
  }
);

onMounted(() => {
  window.addEventListener("keydown", handleEsc);
  if (props.open) document.body.style.overflow = "hidden";
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleEsc);
  document.body.style.overflow = "";
});
</script>

<style scoped>
.issue-drawer-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  z-index: 999;
  backdrop-filter: blur(2px);
}

.issue-drawer {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: min(560px, 92vw);
  background: #fff;
  z-index: 1000;
  box-shadow: -20px 0 50px rgba(15, 23, 42, 0.22);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.issue-drawer__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 22px 14px;
  border-bottom: 1px solid var(--line-soft, rgba(113, 143, 177, 0.24));
  background: #fff;
}

.issue-drawer__head-main {
  flex: 1 1 auto;
  min-width: 0;
}

.issue-drawer__title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.issue-drawer__title-row h3 {
  margin: 0;
  font-size: 17px;
  color: var(--ink-900, #132238);
}

.issue-drawer__subtitle {
  font-size: 12px;
  word-break: break-all;
  line-height: 1.5;
}

.issue-drawer__close {
  flex: 0 0 auto;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--line-soft, rgba(113, 143, 177, 0.24));
  background: #fff;
  color: var(--ink-700, #49627d);
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
  transition: all 0.16s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.issue-drawer__close:hover {
  background: #fee2e2;
  border-color: #b42318;
  color: #b42318;
}

.issue-drawer__body {
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 20px 22px 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.issue-drawer-fade-enter-active,
.issue-drawer-fade-leave-active {
  transition: opacity 0.24s ease;
}

.issue-drawer-fade-enter-from,
.issue-drawer-fade-leave-to {
  opacity: 0;
}

.issue-drawer-slide-enter-active,
.issue-drawer-slide-leave-active {
  transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1);
}

.issue-drawer-slide-enter-from,
.issue-drawer-slide-leave-to {
  transform: translateX(100%);
}
</style>
