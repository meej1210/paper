<template>
  <div :id="anchorId" class="report-hero" :class="{ 'report-hero--serious': variant === 'serious' }">
    <div class="report-hero__content">
      <button
        v-if="showReturnLink"
        class="report-return-link"
        type="button"
        @click="$emit('back')"
      >
        <span aria-hidden="true">←</span>
        {{ returnLabel || '返回管理看板列表' }}
      </button>
      <div class="report-kicker">{{ kicker }}</div>
      <div class="report-hero__title-row">
        <h2>{{ title }}</h2>
        <span v-if="badge" class="report-hero__badge">{{ badge }}</span>
      </div>
      <slot name="badges" />
      <p class="report-summary report-summary--sharp">{{ sharpSummary }}</p>
      <div class="report-pill-row" v-if="pills && pills.length">
        <span v-for="pill in pills" :key="pill" class="report-pill">{{ pill }}</span>
      </div>
      <div v-if="metaItems && metaItems.length" class="report-hero__meta">
        <span v-for="item in metaItems" :key="item">{{ item }}</span>
      </div>
    </div>
    <div class="report-hero__aside">
      <div class="risk-emblem" :class="riskTone.className">
        <span class="risk-emblem__label">{{ riskLabel || '综合风险等级' }}</span>
        <strong>{{ riskTone.label }}</strong>
        <small>{{ riskTone.description }}</small>
      </div>
      <div v-if="actions && actions.length" class="detail-hero__actions report-hero__actions">
        <button
          v-for="action in actions"
          :key="`hero-${action.key}`"
          class="button detail-action-button"
          :class="{ secondary: !action.primary }"
          type="button"
          @click="action.handler"
        >{{ action.label }}</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export type HeroAction = {
  key: string;
  label: string;
  primary: boolean;
  handler: () => void;
};

export type HeroRiskTone = {
  label: string;
  description: string;
  className: string;
};

defineProps<{
  kicker: string;
  title: string;
  badge?: string;
  sharpSummary: string;
  pills?: string[];
  metaItems?: string[];
  riskTone: HeroRiskTone;
  riskLabel?: string;
  actions?: HeroAction[];
  showReturnLink?: boolean;
  returnLabel?: string;
  variant?: "serious" | "default";
  anchorId?: string;
}>();

defineEmits<{ (e: "back"): void }>();
</script>

<style scoped>
.report-summary--sharp {
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.report-return-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: fit-content;
  margin-bottom: 12px;
  border: 0;
  padding: 0;
  color: rgba(248, 251, 255, 0.9);
  background: transparent;
  font: inherit;
  font-size: 13px;
  font-weight: 900;
  cursor: pointer;
}

.report-return-link:hover {
  color: #ffffff;
  text-decoration: underline;
}
</style>
