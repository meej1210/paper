<template>
  <div class="report-action-banner" :class="`report-action-banner--${variant || 'danger'}`">
    <div class="report-action-banner__icon" aria-hidden="true">{{ icon || '⚠' }}</div>
    <div class="report-action-banner__body">
      <strong>{{ title }}</strong>
      <p v-if="message">{{ message }}</p>
    </div>
    <button
      v-if="ctaLabel"
      class="button report-action-banner__cta"
      type="button"
      @click="$emit('cta')"
    >{{ ctaLabel }}</button>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  message?: string;
  ctaLabel?: string;
  icon?: string;
  variant?: "danger" | "warning";
}>();

defineEmits<{ (e: "cta"): void }>();
</script>

<style scoped>
.report-action-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  border-radius: 18px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
}

.report-action-banner--danger {
  background: linear-gradient(135deg, #fff1f2 0%, #ffe4e6 100%);
  border-left: 4px solid #b42318;
  box-shadow: 0 8px 24px rgba(180, 35, 24, 0.12);
}

.report-action-banner--warning {
  background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
  border-left: 4px solid #d97706;
  box-shadow: 0 8px 24px rgba(217, 119, 6, 0.12);
}

.report-action-banner__icon {
  font-size: 26px;
  flex: 0 0 auto;
  line-height: 1;
}

.report-action-banner--danger .report-action-banner__icon {
  color: #b42318;
}

.report-action-banner--warning .report-action-banner__icon {
  color: #b45309;
}

.report-action-banner__body {
  flex: 1 1 auto;
  min-width: 0;
}

.report-action-banner__body strong {
  display: block;
  font-size: 15px;
  font-weight: 800;
  margin-bottom: 4px;
}

.report-action-banner--danger .report-action-banner__body strong {
  color: #7f1d1d;
}

.report-action-banner--warning .report-action-banner__body strong {
  color: #78350f;
}

.report-action-banner__body p {
  margin: 0;
  font-size: 13px;
}

.report-action-banner--danger .report-action-banner__body p {
  color: #b42318;
}

.report-action-banner--warning .report-action-banner__body p {
  color: #b45309;
}

.report-action-banner__cta {
  flex: 0 0 auto;
  color: #fff;
}

.report-action-banner--danger .report-action-banner__cta {
  background: #b42318;
  border-color: #b42318;
}

.report-action-banner--danger .report-action-banner__cta:hover {
  background: #991b1b;
  border-color: #991b1b;
}

.report-action-banner--warning .report-action-banner__cta {
  background: #d97706;
  border-color: #d97706;
}

.report-action-banner--warning .report-action-banner__cta:hover {
  background: #b45309;
  border-color: #b45309;
}
</style>
