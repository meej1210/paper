<template>
  <section class="audit-page">
    <header class="audit-header">
      <div>
        <p class="eyebrow">{{ pageEyebrow }}</p>
        <h2>{{ pageTitle }}</h2>
        <p class="muted">{{ pageDescription }}</p>
      </div>
      <button class="button secondary" type="button" :disabled="loading" @click="reload">刷新</button>
    </header>

    <section class="audit-summary" :aria-label="isAdminViewer ? '审计统计' : '操作统计'">
      <article v-for="card in summaryCards" :key="card.key" class="audit-metric" :class="{ 'audit-metric--danger': card.danger }">
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}</strong>
      </article>
    </section>

    <section v-if="isAdminViewer" class="audit-charts">
      <div class="panel audit-chart-panel">
        <div class="audit-section-head">
          <div>
            <h3>事件类型分布</h3>
            <p class="muted">按审计动作归类统计。</p>
          </div>
        </div>
        <div class="audit-donut-layout">
          <svg class="audit-donut" viewBox="0 0 42 42" aria-label="事件类型饼图">
            <circle class="audit-donut__bg" cx="21" cy="21" r="15.915" fill="none" stroke="#e7eef7" stroke-width="6"></circle>
            <circle
              v-for="slice in visibleDonutSlices"
              :key="slice.label"
              class="audit-donut__slice"
              cx="21"
              cy="21"
              r="15.915"
              fill="none"
              :stroke="slice.color"
              stroke-width="6"
              :stroke-dasharray="`${slice.percent} ${100 - slice.percent}`"
              :stroke-dashoffset="slice.offset"
            ></circle>
            <text x="21" y="20" text-anchor="middle">{{ donutTotal }}</text>
            <text x="21" y="25" text-anchor="middle">事件</text>
          </svg>
          <div class="audit-legend">
            <span v-for="slice in donutSlices" :key="slice.label">
              <i :style="{ background: slice.color }"></i>
              {{ slice.label }} <b>{{ slice.value }}</b>
            </span>
          </div>
        </div>
      </div>

      <div class="panel audit-chart-panel">
        <div class="audit-section-head">
          <div>
            <h3>最近 24 小时操作</h3>
            <p class="muted">按小时聚合审计事件。</p>
          </div>
        </div>
        <div class="audit-hour-bars" aria-label="最近 24 小时柱状图">
          <div v-for="bar in hourBars" :key="bar.hour" class="audit-hour-bar" :title="`${bar.hour}：${bar.count}`">
            <div class="audit-hour-bar__track"><i :style="{ height: bar.percent + '%' }"></i></div>
            <span>{{ bar.hour.slice(0, 2) }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="panel audit-filter-panel">
      <div class="audit-section-head">
        <div>
          <h3>筛选条件</h3>
          <p class="muted">{{ filterDescription }}</p>
        </div>
      </div>
      <div class="audit-filters">
        <label v-if="isAdminViewer" class="field">
          <span>用户关键词</span>
          <input v-model.trim="filters.keyword" class="field-input" type="search" placeholder="用户名、邮箱、动作或详情" @keyup.enter="applyFilters" />
        </label>
        <label class="field">
          <span>动作类型</span>
          <select v-model="filters.action" class="field-input" @change="applyFilters">
            <option value="">全部动作</option>
            <option v-for="option in actionOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
        </label>
        <label class="field">
          <span>结果</span>
          <select v-model="filters.result" class="field-input" @change="applyFilters">
            <option value="">全部结果</option>
            <option value="success">成功</option>
            <option value="created">已创建</option>
            <option value="failed">失败</option>
            <option value="rejected">拒绝</option>
          </select>
        </label>
        <label class="field">
          <span>任务编号</span>
          <input v-model.trim="filters.resource_id" class="field-input" type="search" placeholder="例如 54" @keyup.enter="applyFilters" />
        </label>
        <label class="field">
          <span>开始时间</span>
          <input v-model="filters.start_time" class="field-input" type="datetime-local" />
        </label>
        <label class="field">
          <span>结束时间</span>
          <input v-model="filters.end_time" class="field-input" type="datetime-local" />
        </label>
        <div class="audit-filter-actions">
          <button class="button" type="button" :disabled="loading" @click="applyFilters">查询</button>
          <button class="button secondary" type="button" :disabled="loading" @click="resetFilters">重置</button>
        </div>
      </div>
    </section>

    <section class="panel audit-table-panel">
      <div class="audit-section-head">
        <div>
          <h3>{{ tableTitle }}</h3>
          <p class="muted">第 {{ pagination.page }} 页 / 共 {{ totalPages }} 页，合计 {{ pagination.total }} 条。</p>
        </div>
      </div>

      <div v-if="errorMessage" class="error">{{ errorMessage }}</div>
      <div v-else-if="loading" class="empty-state loading-state">正在加载{{ pageTitle }}...</div>
      <div v-else-if="!logs.length" class="empty-state">
        <h4>暂无{{ pageTitle }}</h4>
        <p>当前筛选条件下没有可展示的操作记录。</p>
      </div>

      <div v-else class="audit-table-wrap">
        <table class="table audit-table">
          <thead>
            <tr>
              <th>时间</th>
              <th v-if="isAdminViewer">用户</th>
              <th v-if="isAdminViewer">角色</th>
              <th>动作</th>
              <th>资源</th>
              <th>结果</th>
              <th v-if="isAdminViewer">IP</th>
              <th>详情</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="item in logs" :key="item.id">
              <tr>
                <td>{{ formatTime(item.created_at) }}</td>
                <td v-if="isAdminViewer">
                  <div class="audit-user">
                    <strong>{{ item.user?.username || "未知用户" }}</strong>
                    <span>{{ item.user?.email || "-" }}</span>
                  </div>
                </td>
                <td v-if="isAdminViewer">{{ roleLabel(item.user?.role) }}</td>
                <td><span class="audit-action-tag" :class="actionTone(item.action)">{{ item.action_label || actionLabel(item.action) }}</span></td>
                <td>{{ resourceLabel(item) }}</td>
                <td><span class="audit-result-tag" :class="`audit-result-tag--${resultTone(item.result)}`">{{ resultLabel(item.result) }}</span></td>
                <td v-if="isAdminViewer">{{ item.ip_address || "-" }}</td>
                <td>
                  <button class="audit-link-button" type="button" @click="toggleDetail(item.id)">
                    {{ expandedIds.has(item.id) ? "收起" : "展开" }}
                  </button>
                </td>
              </tr>
              <tr v-if="expandedIds.has(item.id)" class="audit-detail-row">
                <td :colspan="detailColspan">
                  <div class="audit-detail">
                    <div class="audit-detail__summary">
                      <span>动作：{{ item.action_label || actionLabel(item.action) }}</span>
                      <span v-if="isAdminViewer">用户：{{ item.user?.username || "-" }}</span>
                      <span>资源：{{ resourceLabel(item) }}</span>
                      <span>结果：{{ resultLabel(item.result) }}</span>
                    </div>
                    <pre v-if="isAdminViewer">{{ detailText(item.detail) }}</pre>
                    <p v-else class="audit-detail__note">{{ userDetailSummary(item) }}</p>
                    <RouterLink v-if="item.report_route" class="audit-report-link" :to="item.report_route">查看任务报告</RouterLink>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <div class="pagination audit-pagination">
        <span>当前展示 {{ logs.length }} 条</span>
        <div class="nav">
          <button class="button secondary button--small" type="button" :disabled="pagination.page <= 1 || loading" @click="prevPage">上一页</button>
          <button class="button secondary button--small" type="button" :disabled="pagination.page >= totalPages || loading" @click="nextPage">下一页</button>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";
import { listAuditLogs, type AuditLogParams } from "../api/audit";

type AuditUser = {
  id: number;
  username: string;
  email: string;
  role: string;
};

type AuditItem = {
  id: number;
  created_at: string;
  user: AuditUser | null;
  action: string;
  action_label?: string;
  resource_type?: string | null;
  resource_id?: string | null;
  result?: string | null;
  ip_address?: string | null;
  detail?: unknown;
  report_route?: string | null;
};

type AuditSummary = {
  today_count: number;
  login_failed_count: number;
  task_create_count: number;
  report_view_count: number;
  report_export_count: number;
  dast_authorized_count: number;
};

type AuditViewer = {
  id: number;
  username: string;
  email: string;
  role: string;
};

const logs = ref<AuditItem[]>([]);
const viewer = ref<AuditViewer | null>(null);
const summary = ref<AuditSummary>({
  today_count: 0,
  login_failed_count: 0,
  task_create_count: 0,
  report_view_count: 0,
  report_export_count: 0,
  dast_authorized_count: 0
});
const charts = ref<{ by_action: Record<string, number>; by_hour_24h: Array<{ hour: string; count: number }> }>({ by_action: {}, by_hour_24h: [] });
const loading = ref(false);
const errorMessage = ref("");
const expandedIds = ref(new Set<number>());
const pagination = reactive({ page: 1, page_size: 20, total: 0 });
const filters = reactive({ keyword: "", action: "", result: "", resource_id: "", start_time: "", end_time: "" });
const isAdminViewer = computed(() => viewer.value?.role === "admin");
const pageEyebrow = computed(() => isAdminViewer.value ? "平台审计" : "个人记录");
const pageTitle = computed(() => isAdminViewer.value ? "审计日志" : "我的操作记录");
const pageDescription = computed(() =>
  isAdminViewer.value ? "追踪登录、扫描、报告访问、导出和 DAST 授权行为。" : "查看本人登录、扫描、报告访问、导出和 DAST 授权记录。"
);
const filterDescription = computed(() =>
  isAdminViewer.value ? "按用户、动作、结果、时间和任务编号定位操作证据。" : "按动作、结果、时间和任务编号定位自己的操作记录。"
);
const tableTitle = computed(() => isAdminViewer.value ? "操作证据" : "操作记录");
const detailColspan = computed(() => isAdminViewer.value ? 8 : 5);

const actionOptions = [
  { value: "AUTH_LOGIN_SUCCESS", label: "登录成功" },
  { value: "AUTH_LOGIN_FAILED", label: "登录失败" },
  { value: "TASK_CREATE", label: "创建扫描任务" },
  { value: "TASK_CANCEL", label: "取消任务" },
  { value: "TASK_RERUN", label: "重新执行任务" },
  { value: "REPORT_VIEW", label: "查看报告" },
  { value: "REPORT_DOWNLOAD_JSON", label: "下载 JSON 报告" },
  { value: "REPORT_EXPORT_HTML", label: "导出 HTML 报告" },
  { value: "REPORT_EXPORT_PDF", label: "导出 PDF 报告" },
  { value: "DAST_AUTH_CONFIRMED", label: "DAST 授权确认" },
  { value: "DAST_AUTH_REJECTED", label: "DAST 授权拒绝" },
  { value: "ADMIN_DASHBOARD_VIEW", label: "访问管理看板" },
  { value: "ADMIN_TASK_VIEW", label: "管理员查看用户任务" }
];

const actionLabels = Object.fromEntries(actionOptions.map((item) => [item.value, item.label]));
const totalPages = computed(() => Math.max(1, Math.ceil(pagination.total / pagination.page_size)));
const summaryCards = computed(() => [
  { key: "today", label: isAdminViewer.value ? "今日操作" : "我的今日操作", value: summary.value.today_count },
  { key: "failed", label: "登录失败", value: summary.value.login_failed_count, danger: summary.value.login_failed_count > 0 },
  { key: "task", label: "创建扫描", value: summary.value.task_create_count },
  { key: "view", label: "报告访问", value: summary.value.report_view_count },
  { key: "export", label: "报告导出", value: summary.value.report_export_count },
  { key: "dast", label: "DAST 授权", value: summary.value.dast_authorized_count }
]);

const categoryRows = computed(() => {
  const byAction = charts.value.by_action || {};
  return [
    { label: "认证登录", value: countActions(byAction, ["AUTH_LOGIN_SUCCESS", "AUTH_LOGIN_FAILED", "AUTH_LOGOUT"]), color: "#2563eb" },
    { label: "扫描任务", value: countActions(byAction, ["TASK_CREATE", "TASK_CANCEL", "TASK_RERUN", "TASK_STATUS_CHANGE"]), color: "#16a34a" },
    { label: "报告访问", value: countActions(byAction, ["REPORT_VIEW"]), color: "#0f7990" },
    { label: "报告导出", value: countActions(byAction, ["REPORT_DOWNLOAD_JSON", "REPORT_EXPORT_HTML", "REPORT_EXPORT_PDF"]), color: "#d97706" },
    { label: "DAST 授权", value: countActions(byAction, ["DAST_AUTH_CONFIRMED", "DAST_AUTH_REJECTED"]), color: "#dc2626" },
    { label: "管理员操作", value: countActions(byAction, ["ADMIN_DASHBOARD_VIEW", "ADMIN_TASK_VIEW"]), color: "#475569" }
  ];
});
const donutTotal = computed(() => Math.max(categoryRows.value.reduce((sum, row) => sum + row.value, 0), 0));
const donutSlices = computed(() => {
  const total = Math.max(donutTotal.value, 1);
  let offset = 25;
  return categoryRows.value.map((row) => {
    const percent = Math.round((row.value / total) * 1000) / 10;
    const slice = { ...row, percent, offset };
    offset -= percent;
    return slice;
  });
});
const visibleDonutSlices = computed(() => donutSlices.value.filter((slice) => slice.value > 0));
const hourBars = computed(() => {
  const rows = charts.value.by_hour_24h || [];
  const max = Math.max(...rows.map((row) => row.count), 1);
  return rows.map((row) => ({ ...row, percent: row.count ? Math.max(8, Math.round((row.count / max) * 100)) : 0 }));
});

function countActions(source: Record<string, number>, keys: string[]) {
  return keys.reduce((sum, key) => sum + Number(source[key] || 0), 0);
}

function buildParams(): AuditLogParams {
  const params: AuditLogParams = { page: pagination.page, page_size: pagination.page_size };
  if (isAdminViewer.value && filters.keyword) params.keyword = filters.keyword;
  if (filters.action) params.action = filters.action;
  if (filters.result) params.result = filters.result;
  if (filters.resource_id) params.resource_id = filters.resource_id;
  if (filters.start_time) params.start_time = new Date(filters.start_time).toISOString().slice(0, 19);
  if (filters.end_time) params.end_time = new Date(filters.end_time).toISOString().slice(0, 19);
  return params;
}

async function loadLogs() {
  loading.value = true;
  errorMessage.value = "";
  try {
    const response = await listAuditLogs(buildParams());
    const data = response.data || {};
    logs.value = data.items || [];
    viewer.value = data.viewer || null;
    Object.assign(pagination, data.pagination || pagination);
    summary.value = { ...summary.value, ...(data.summary || {}) };
    charts.value = data.charts || { by_action: {}, by_hour_24h: [] };
  } catch (error: any) {
    logs.value = [];
    pagination.total = 0;
    errorMessage.value = error.response?.data?.message || "审计日志加载失败，请确认登录状态和后端服务。";
  } finally {
    loading.value = false;
  }
}

function reload() {
  void loadLogs();
}

function applyFilters() {
  pagination.page = 1;
  expandedIds.value = new Set();
  void loadLogs();
}

function resetFilters() {
  Object.assign(filters, { keyword: "", action: "", result: "", resource_id: "", start_time: "", end_time: "" });
  pagination.page = 1;
  expandedIds.value = new Set();
  void loadLogs();
}

function prevPage() {
  if (pagination.page <= 1) return;
  pagination.page -= 1;
  void loadLogs();
}

function nextPage() {
  if (pagination.page >= totalPages.value) return;
  pagination.page += 1;
  void loadLogs();
}

function toggleDetail(id: number) {
  const next = new Set(expandedIds.value);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  expandedIds.value = next;
}

function actionLabel(action: string) {
  return actionLabels[action] || action;
}

function actionTone(action: string) {
  if (action.includes("FAILED") || action.includes("REJECTED")) return "audit-action-tag--danger";
  if (action.startsWith("REPORT")) return "audit-action-tag--report";
  if (action.startsWith("DAST")) return "audit-action-tag--dast";
  if (action.startsWith("ADMIN")) return "audit-action-tag--admin";
  return "audit-action-tag--default";
}

function resultTone(value?: string | null) {
  const normalized = String(value || "").toLowerCase();
  if (normalized === "failed" || normalized === "rejected") return "danger";
  if (normalized === "created") return "info";
  return "success";
}

function resultLabel(value?: string | null) {
  const labels: Record<string, string> = { success: "成功", created: "已创建", failed: "失败", rejected: "拒绝" };
  return labels[String(value || "").toLowerCase()] || value || "-";
}

function roleLabel(value?: string) {
  return value === "admin" ? "管理员" : "普通用户";
}

function resourceLabel(item: AuditItem) {
  if (!item.resource_type && !item.resource_id) return "-";
  const type = item.resource_type === "task" ? "任务" : item.resource_type === "user" ? "用户" : item.resource_type || "资源";
  return item.resource_id ? `${type} #${item.resource_id}` : type;
}

function detailText(detail: unknown) {
  if (detail === null || detail === undefined || detail === "") return "无结构化详情";
  if (typeof detail === "string") return detail;
  return JSON.stringify(detail, null, 2);
}

function userDetailSummary(item: AuditItem) {
  const action = item.action_label || actionLabel(item.action);
  const resource = resourceLabel(item);
  const result = resultLabel(item.result);
  if (resource === "-") return `${action}，结果：${result}。`;
  return `${action}，${resource}，结果：${result}。`;
}

function formatTime(value?: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

onMounted(() => {
  void loadLogs();
});
</script>

<style scoped>
.audit-page { display: grid; gap: 16px; color: #0f172a; }
.audit-header { display: flex; gap: 16px; align-items: flex-start; justify-content: space-between; }
.audit-header h2 { margin: 4px 0 8px; color: #102a43; font-size: 32px; line-height: 1.15; }
.eyebrow { margin: 0; color: #0f7990; font-size: 12px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; }
.audit-summary { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; }
.audit-metric { min-height: 82px; display: grid; align-content: center; gap: 6px; padding: 14px; border: 1px solid #dbe7f2; border-radius: 8px; background: #ffffff; box-shadow: 0 10px 24px rgba(20, 33, 61, .06); }
.audit-metric span { color: #526477; font-size: 13px; font-weight: 800; }
.audit-metric strong { color: #102a43; font-size: 28px; line-height: 1; }
.audit-metric--danger { border-color: rgba(180, 35, 24, .28); background: #fff7f5; }
.audit-metric--danger strong { color: #b42318; }
.audit-charts { display: grid; grid-template-columns: minmax(320px, .9fr) minmax(420px, 1.1fr); gap: 16px; }
.audit-chart-panel, .audit-filter-panel, .audit-table-panel { border-radius: 8px; }
.audit-section-head { display: flex; justify-content: space-between; gap: 14px; align-items: flex-start; margin-bottom: 16px; }
.audit-section-head h3 { margin: 0 0 4px; color: #102a43; font-size: 18px; }
.audit-donut-layout { display: grid; grid-template-columns: 168px minmax(0, 1fr); gap: 18px; align-items: center; }
.audit-donut { width: 168px; height: 168px; transform: rotate(-90deg); }
.audit-donut__bg { fill: none; stroke: #e7eef7; stroke-width: 6; }
.audit-donut__slice { fill: none; stroke-width: 6; }
.audit-donut text { transform: rotate(90deg); transform-origin: 21px 21px; fill: #102a43; font-weight: 900; }
.audit-donut text:first-of-type { font-size: 7px; }
.audit-donut text:last-of-type { fill: #64748b; font-size: 3px; }
.audit-legend { display: grid; gap: 9px; }
.audit-legend span { display: grid; grid-template-columns: 10px minmax(0, 1fr) auto; gap: 8px; align-items: center; font-size: 13px; font-weight: 800; }
.audit-legend i { width: 10px; height: 10px; border-radius: 999px; }
.audit-hour-bars { height: 176px; display: grid; grid-template-columns: repeat(24, minmax(8px, 1fr)); gap: 5px; align-items: end; }
.audit-hour-bar { min-width: 0; display: grid; grid-template-rows: 1fr auto; gap: 6px; text-align: center; }
.audit-hour-bar__track { position: relative; height: 136px; border-radius: 6px; background: #eef4fb; overflow: hidden; }
.audit-hour-bar__track i { position: absolute; inset: auto 0 0; border-radius: 6px 6px 0 0; background: linear-gradient(180deg, #0f7990, #17324d); }
.audit-hour-bar span { color: #64748b; font-size: 10px; font-weight: 800; }
.audit-filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 190px), 1fr)); gap: 12px; align-items: end; }
.audit-filters .field { min-width: 0; }
.audit-filters input[type="datetime-local"] { min-width: 0; }
.audit-filter-actions { display: flex; gap: 10px; align-self: end; }
.audit-filter-actions .button { white-space: nowrap; }
.audit-table-wrap { overflow-x: auto; border: 1px solid #dbe7f2; border-radius: 8px; }
.audit-table { min-width: 1120px; }
.audit-table th { color: #526477; font-size: 12px; }
.audit-user { display: grid; gap: 4px; }
.audit-user strong { color: #102a43; }
.audit-user span { color: #64748b; font-size: 12px; font-weight: 700; }
.audit-action-tag, .audit-result-tag { display: inline-flex; align-items: center; justify-content: center; min-width: 72px; border-radius: 999px; padding: 6px 10px; font-size: 12px; font-weight: 900; white-space: nowrap; }
.audit-action-tag--default { background: #e0f2fe; color: #075985; }
.audit-action-tag--report { background: #dcfce7; color: #166534; }
.audit-action-tag--dast { background: #fef3c7; color: #92400e; }
.audit-action-tag--admin { background: #e2e8f0; color: #334155; }
.audit-action-tag--danger { background: #fee2e2; color: #991b1b; }
.audit-result-tag--success { background: #dcfce7; color: #166534; }
.audit-result-tag--info { background: #e0f2fe; color: #075985; }
.audit-result-tag--danger { background: #fee2e2; color: #991b1b; }
.audit-link-button { border: 0; padding: 0; color: #0f7990; background: transparent; cursor: pointer; font-weight: 900; }
.audit-detail-row td { background: #f8fbff; }
.audit-detail { display: grid; gap: 12px; padding: 6px 0; }
.audit-detail__summary { display: flex; flex-wrap: wrap; gap: 10px; color: #334155; font-size: 13px; font-weight: 800; }
.audit-detail pre { max-height: 260px; margin: 0; padding: 14px; border-radius: 8px; overflow: auto; color: #e2e8f0; background: #0f172a; white-space: pre-wrap; word-break: break-word; }
.audit-report-link { width: fit-content; border-radius: 999px; padding: 8px 12px; color: #fff; background: #17324d; font-weight: 900; }
.audit-pagination { margin-top: 16px; }
@media (max-width: 1280px) { .audit-summary { grid-template-columns: repeat(3, 1fr); } .audit-charts { grid-template-columns: 1fr; } .audit-filter-actions { justify-content: flex-start; } }
@media (max-width: 720px) { .audit-header { flex-direction: column; } .audit-summary { grid-template-columns: repeat(2, 1fr); } .audit-donut-layout { grid-template-columns: 1fr; justify-items: center; } .audit-hour-bars { gap: 3px; } .audit-filter-actions { flex-direction: column; } }
</style>
