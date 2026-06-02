<template>
  <div class="app-stage" :class="appAtmosphereClass">
    <div class="app-atmosphere" aria-hidden="true">
      <span class="app-atmosphere__blob app-atmosphere__blob--a"></span>
      <span class="app-atmosphere__blob app-atmosphere__blob--b"></span>
      <span class="app-atmosphere__blob app-atmosphere__blob--c"></span>
      <span class="app-atmosphere__grid"></span>
      <span class="app-atmosphere__ring"></span>
      <span class="app-atmosphere__beam"></span>

      <!-- Radar sweep -->
      <span class="soc-radar">
        <span class="soc-radar__sweep"></span>
        <span class="soc-radar__ring soc-radar__ring--1"></span>
        <span class="soc-radar__ring soc-radar__ring--2"></span>
        <span class="soc-radar__ring soc-radar__ring--3"></span>
        <span class="soc-radar__cross soc-radar__cross--h"></span>
        <span class="soc-radar__cross soc-radar__cross--v"></span>
        <span class="soc-radar__dot soc-radar__dot--a"></span>
        <span class="soc-radar__dot soc-radar__dot--b"></span>
        <span class="soc-radar__dot soc-radar__dot--c"></span>
        <span class="soc-radar__dot soc-radar__dot--d"></span>
        <span class="soc-radar__dot soc-radar__dot--e"></span>
      </span>

      <!-- Topology nodes -->
      <span class="soc-topo">
        <span class="soc-topo__node soc-topo__node--1"></span>
        <span class="soc-topo__node soc-topo__node--2"></span>
        <span class="soc-topo__node soc-topo__node--3"></span>
        <span class="soc-topo__node soc-topo__node--4"></span>
        <span class="soc-topo__node soc-topo__node--5"></span>
        <span class="soc-topo__node soc-topo__node--6"></span>
        <span class="soc-topo__node soc-topo__node--7"></span>
        <span class="soc-topo__node soc-topo__node--8"></span>
        <span class="soc-topo__link soc-topo__link--a"></span>
        <span class="soc-topo__link soc-topo__link--b"></span>
        <span class="soc-topo__link soc-topo__link--c"></span>
        <span class="soc-topo__link soc-topo__link--d"></span>
        <span class="soc-topo__link soc-topo__link--e"></span>
      </span>

      <!-- Scan lines -->
      <span class="soc-scanlines"></span>
      <span class="soc-scanline soc-scanline--h"></span>
      <span class="soc-scanline soc-scanline--v"></span>

      <!-- Hex grid -->
      <span class="soc-hexgrid"></span>
    </div>

    <div class="app-shell" :class="{ 'app-shell--auth-only': isAuthRoute }">
      <header v-if="!isAuthRoute" class="panel panel--chrome app-header">
        <RouterLink class="app-brand" :to="authenticated ? '/tasks' : '/login'">
          <div class="app-brand__mark" aria-hidden="true">
            <span class="app-brand__mark-core">DS</span>
            <span class="app-brand__mark-node app-brand__mark-node--a"></span>
            <span class="app-brand__mark-node app-brand__mark-node--b"></span>
            <span class="app-brand__mark-node app-brand__mark-node--c"></span>
          </div>

          <div class="app-brand__copy">
            <p class="eyebrow">安全审计控制台</p>
            <div class="app-brand__title-row">
              <h1>安全审计工作台</h1>
              <span class="app-brand__badge">静态 / 动态 / 依赖</span>
            </div>
            <p class="muted">任务、扫描、报告一屏直达。</p>
          </div>
        </RouterLink>

        <div class="app-header__right">
          <nav class="app-nav" v-if="authenticated">
            <RouterLink to="/tasks">工作台</RouterLink>
            <RouterLink to="/scan/new">新建扫描</RouterLink>
            <RouterLink v-if="currentUser?.role === 'admin'" to="/admin" :class="{ 'router-link-active': isAdminContextRoute, 'router-link-exact-active': isAdminContextRoute }">管理看板</RouterLink>
            <RouterLink to="/audit-logs">{{ auditNavLabel }}</RouterLink>
          </nav>

          <div class="app-user" v-if="authenticated">
            <div class="app-user__avatar" aria-hidden="true">{{ userInitial }}</div>
            <div class="app-user__meta">
              <strong>{{ currentUser?.username || '已登录用户' }}</strong>
            </div>
            <button class="app-user__logout" @click="logout">退出登录</button>
          </div>

        </div>
      </header>

      <RouterView v-slot="{ Component, route: viewRoute }">
        <Transition name="page-swap" mode="out-in">
          <component :is="Component" :key="viewRoute.fullPath" />
        </Transition>
      </RouterView>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getCurrentUser } from "./api/auth";
import { clearToken, isAuthenticated } from "./store/auth";

const router = useRouter();
const route = useRoute();
const currentUser = ref<any>(null);
const authenticated = computed(() => isAuthenticated());
const isAuthRoute = computed(() => route.path === "/login");
const userInitial = computed(() => {
  const username = String(currentUser.value?.username || "").trim();
  if (!username) return "U";
  return username.slice(0, 1).toUpperCase();
});
const isAdminContextRoute = computed(() => route.path === "/admin" || (currentUser.value?.role === "admin" && route.path.startsWith("/tasks/")));
const isAdminUser = computed(() => currentUser.value?.role === "admin");
const auditNavLabel = computed(() => isAdminUser.value ? "审计日志" : "操作记录");

const pageTitle = computed(() => String(route.meta.title || (authenticated.value ? "工作台" : "欢迎使用")));
const pageDescription = computed(() => String(route.meta.description || "统一管理扫描任务、报告和审计流程。"));
const breadcrumb = computed(() => `${authenticated.value ? "安全运营" : "访客入口"} / ${pageTitle.value}`);
const pageContext = computed(() => {
  if (route.path === "/login") {
    return {
      badge: "登录入口",
      highlights: ["统一登录入口", "进入任务工作台", "适合答辩演示"]
    };
  }

  if (route.path === "/register") {
    return {
      badge: "账号注册",
      highlights: ["创建平台账号", "任务可追踪", "审计链路清晰"]
    };
  }

  if (route.path === "/scan/new") {
    return {
      badge: route.query.type === "dast" ? "动态扫描流程" : "静态审计流程",
      highlights: ["统一建任务入口", "按场景切换模式", "减少纯表单感"]
    };
  }

  if (route.path.startsWith("/tasks/")) {
    return {
      badge: "报告详情",
      highlights: ["先看结论", "再看证据", "最后导出报告"]
    };
  }

  if (route.path === "/admin") {
    return {
      badge: "管理看板",
      highlights: ["全局任务统计", "风险摘要", "授权边界审计"]
    };
  }

  if (route.path === "/audit-logs") {
    return {
      badge: isAdminUser.value ? "审计日志" : "操作记录",
      highlights: isAdminUser.value ? ["操作可回溯", "便于复核", "支持管理员巡检"] : ["只看本人记录", "任务操作可追踪", "报告访问可回看"]
    };
  }

  return {
    badge: "任务工作台",
    highlights: ["任务集中查看", "状态快速筛选", "结果统一跟进"]
  };
});
const pageBannerClass = computed(() => {
  if (route.path === "/login" || route.path === "/register") return "page-banner--auth";
  if (route.path === "/scan/new") return "page-banner--scan";
  if (route.path.startsWith("/tasks/")) return "page-banner--detail";
  if (route.path === "/admin") return "page-banner--audit";
  if (route.path === "/audit-logs") return "page-banner--audit";
  return "page-banner--workspace";
});
const appAtmosphereClass = computed(() => {
  if (route.path === "/login" || route.path === "/register") return "app-stage--auth";
  if (route.path === "/scan/new") return "app-stage--scan";
  if (route.path.startsWith("/tasks/")) return "app-stage--detail";
  if (route.path === "/admin") return "app-stage--audit";
  if (route.path === "/audit-logs") return "app-stage--audit";
  return "app-stage--workspace";
});

async function loadCurrentUser() {
  if (!authenticated.value) {
    currentUser.value = null;
    return;
  }

  try {
    const response = await getCurrentUser();
    currentUser.value = response.data.user;
  } catch {
    currentUser.value = null;
  }
}

function logout() {
  clearToken();
  currentUser.value = null;
  router.push("/login");
}

watch([authenticated, () => route.fullPath], () => {
  void loadCurrentUser();
}, { immediate: true });
</script>
