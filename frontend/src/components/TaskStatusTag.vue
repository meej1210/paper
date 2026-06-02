<template>
  <span class="tag" :class="normalized">
    <span class="tag__dot"></span>
    <span>{{ status }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ status: string }>();
const normalized = computed(() => props.status.toLowerCase());
</script>
