<template>
  <section class="admin-scans-page">
    <div v-if="permissionDenied" class="panel admin-denied">
      <p class="eyebrow">权限不足</p>
      <h2>无权限访问管理页面</h2>
      <p>当前账号不是管理员。普通用户只能查看自己的扫描任务。</p>
    </div>

    <template v-else>
      <section class="admin-scan-hero">
        <div class="admin-scan-hero__intro">
          <p class="eyebrow">管理员 / 全用户扫描记录</p>
          <h2>所有用户扫描与报告</h2>
          <p>管理员在这里查看所有用户发起的扫描任务，并直接进入报告。</p>
          <div class="hero-metrics-strip">
            <span><b>{{ totalCount }}</b> 全部扫描</span>
            <span><b>{{ totals.success || 0 }}</b> 已完成</span>
            <span><b>{{ (totals.running || 0) + (totals.pending || 0) }}</b> 运行/排队</span>
            <span><b>{{ totals.failed || 0 }}</b> 需复核</span>
          </div>
        </div>

        <div class="admin-chart-card">
          <div class="chart-heading">
            <strong>扫描类型占比</strong>
            <span>静态 / 动态 / 依赖</span>
          </div>
          <div class="donut-wrap">
            <svg class="donut-chart" viewBox="0 0 42 42" aria-label="扫描类型饼状图">
              <circle class="donut-bg" cx="21" cy="21" r="15.915"></circle>
              <circle
                v-for="slice in typeDonutSlices"
                :key="slice.label"
                class="donut-slice"
                cx="21"
                cy="21"
                r="15.915"
                :stroke="slice.color"
                :stroke-dasharray="`${slice.percent} ${100 - slice.percent}`"
                :stroke-dashoffset="slice.offset"
              ></circle>
              <text x="21" y="20" text-anchor="middle">{{ totalCount }}</text>
              <text x="21" y="25" text-anchor="middle">总数</text>
            </svg>
            <div class="chart-legend">
              <span v-for="slice in typeDonutSlices" :key="slice.label">
                <i :style="{ background: slice.color }"></i>{{ slice.label }} {{ slice.value }}
              </span>
            </div>
          </div>
        </div>

        <div class="admin-chart-card">
          <div class="chart-heading">
            <strong>状态分布</strong>
            <span>任务处理进度</span>
          </div>
          <div class="bar-chart" aria-label="状态柱状图">
            <div v-for="bar in statusBars" :key="bar.label" class="bar-chart__item">
              <div class="bar-chart__track"><i :style="{ height: bar.percent + '%', background: bar.color }"></i></div>
              <strong>{{ bar.value }}</strong>
              <span>{{ bar.label }}</span>
            </div>
          </div>
        </div>
      </section>

      <section class="panel admin-task-panel">
        <div class="section-heading admin-task-heading">
          <div>
            <p class="eyebrow">扫描列表</p>
            <h3>全平台扫描任务</h3>
            <p class="muted">包含任务所属用户、扫描类型、目标、状态、创建时间和报告入口。</p>
          </div>
          <button class="button secondary" type="button" :disabled="loading" @click="reloadAll">刷新</button>
        </div>

        <div class="admin-filters">
          <label class="field-label">
            搜索用户/任务/目标
            <input v-model.trim="filters.keyword" class="field-input" type="search" placeholder="例如 admin@qq.com、任务名、目标 URL" @keyup.enter="applyFilters" />
          </label>
          <label class="field-label">
            扫描类型
            <select v-model="filters.task_type" class="field-input" @change="applyFilters">
              <option value="">全部类型</option>
              <option value="SAST">SAST 静态审计</option>
              <option value="DAST">DAST 动态扫描</option>
              <option value="SCA">SCA 依赖审计</option>
            </select>
          </label>
          <label class="field-label">
            任务状态
            <select v-model="filters.status" class="field-input" @change="applyFilters">
              <option value="">全部状态</option>
              <option value="PENDING">排队中</option>
              <option value="RUNNING">执行中</option>
              <option value="SUCCESS">已完成</option>
              <option value="FAILED">失败</option>
              <option value="TIMEOUT">超时</option>
              <option value="CANCELLED">已取消</option>
            </select>
          </label>
          <div class="admin-filter-actions">
            <button class="button" type="button" :disabled="loading" @click="applyFilters">查询</button>
            <button class="button secondary" type="button" :disabled="loading" @click="resetFilters">重置</button>
          </div>
        </div>

        <div v-if="errorMessage" class="error">{{ errorMessage }}</div>
        <div v-else-if="loading" class="empty-state loading-state">正在加载全平台扫描记录...</div>
        <div v-else-if="!tasks.length" class="empty-state">
          <h4>暂无扫描记录</h4>
          <p>当前筛选条件下没有任何用户扫描任务。</p>
        </div>

        <div v-else class="admin-table-wrap">
          <table class="table admin-task-table">
            <thead>
              <tr>
                <th>用户</th>
                <th>扫描任务</th>
                <th>类型</th>
                <th>目标</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>报告</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="task in tasks" :key="task.id">
                <td>
                  <div class="user-cell">
                    <strong>{{ task.user?.username || '-' }}</strong>
                    <span>{{ task.user?.email || '-' }}</span>
                  </div>
                </td>
                <td>
                  <div class="task-cell">
                    <strong>{{ task.task_name || `扫描任务 #${task.id}` }}</strong>
                    <span>平台编号 #{{ task.id }} / 用户内编号 #{{ task.user_task_no || '-' }}</span>
                  </div>
                </td>
                <td><span class="type-pill" :class="`type-pill--${String(task.task_type).toLowerCase()}`">{{ taskTypeLabel(task.task_type) }}</span></td>
                <td class="target-cell">{{ task.target_url || task.target_name || '-' }}</td>
                <td><span class="status-pill" :class="`status-pill--${String(task.status).toLowerCase()}`">{{ statusLabel(task.status) }}</span></td>
                <td>{{ formatTime(task.created_at) }}</td>
                <td>
                  <RouterLink class="report-link" :to="task.report_route || `/tasks/${task.id}?type=${task.task_type}&from=admin`">
                    {{ task.status === 'SUCCESS' ? '查看报告' : '查看详情' }}
                  </RouterLink>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pagination admin-pagination">
          <span>第 {{ pagination.page }} 页 / 共 {{ totalPages }} 页，合计 {{ pagination.total }} 条</span>
          <div>
            <button class="button secondary button--small" type="button" :disabled="pagination.page <= 1 || loading" @click="prevPage">上一页</button>
            <button class="button secondary button--small" type="button" :disabled="pagination.page >= totalPages || loading" @click="nextPage">下一页</button>
          </div>
        </div>
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { RouterLink } from "vue-router";
import { getAdminDashboard, listAdminTasks } from "../api/admin";

const dashboard = ref<any>(null);
const tasks = ref<any[]>([]);
const loading = ref(false);
const errorMessage = ref("");
const permissionDenied = ref(false);
const pagination = reactive({ page: 1, page_size: 12, total: 0 });
const filters = reactive({ keyword: "", task_type: "", status: "" });

const totals = computed(() => dashboard.value?.task_totals || { total: 0, success: 0, failed: 0, running: 0, pending: 0 });
const totalCount = computed(() => pagination.total || totals.value.total || 0);
const totalPages = computed(() => Math.max(1, Math.ceil(pagination.total / pagination.page_size)));
const typeDonutSlices = computed(() => {
  const byType = dashboard.value?.task_totals?.by_type || {};
  const rows = [
    { label: "SAST", value: Number(byType.SAST || 0), color: "#38bdf8" },
    { label: "DAST", value: Number(byType.DAST || 0), color: "#22c55e" },
    { label: "SCA", value: Number(byType.SCA || 0), color: "#f59e0b" }
  ];
  const total = Math.max(rows.reduce((sum, item) => sum + item.value, 0), 1);
  let offset = 25;
  return rows.map((item) => {
    const percent = Math.max(0, Math.round((item.value / total) * 1000) / 10);
    const slice = { ...item, percent, offset };
    offset -= percent;
    return slice;
  });
});
const statusBars = computed(() => {
  const byStatus = dashboard.value?.task_totals?.by_status || {};
  const rows = [
    { label: "完成", value: Number(byStatus.SUCCESS || 0), color: "#16a34a" },
    { label: "运行", value: Number(byStatus.RUNNING || 0), color: "#0284c7" },
    { label: "排队", value: Number(byStatus.PENDING || 0), color: "#7c3aed" },
    { label: "失败", value: Number(byStatus.FAILED || 0), color: "#dc2626" },
    { label: "超时", value: Number(byStatus.TIMEOUT || 0), color: "#ea580c" },
    { label: "取消", value: Number(byStatus.CANCELLED || 0), color: "#475569" }
  ];
  const max = Math.max(...rows.map((item) => item.value), 1);
  return rows.map((item) => ({ ...item, percent: Math.max(4, Math.round((item.value / max) * 100)) }));
});

async function loadDashboard() {
  const response = await getAdminDashboard();
  dashboard.value = response.data;
}

async function loadTasks() {
  loading.value = true;
  errorMessage.value = "";
  permissionDenied.value = false;
  try {
    await loadDashboard();
    const params: Record<string, string | number> = { page: pagination.page, page_size: pagination.page_size };
    if (filters.keyword) params.keyword = filters.keyword;
    if (filters.task_type) params.task_type = filters.task_type;
    if (filters.status) params.status = filters.status;
    const response = await listAdminTasks(params);
    tasks.value = response.data.items || [];
    Object.assign(pagination, response.data.pagination || pagination);
  } catch (error: any) {
    if (error.response?.status === 403) {
      permissionDenied.value = true;
    } else {
      errorMessage.value = error.response?.data?.message || "全平台扫描记录加载失败，请确认后端服务和管理员登录状态。";
    }
  } finally {
    loading.value = false;
  }
}

function reloadAll() {
  void loadTasks();
}

function applyFilters() {
  pagination.page = 1;
  void loadTasks();
}

function resetFilters() {
  filters.keyword = "";
  filters.task_type = "";
  filters.status = "";
  pagination.page = 1;
  void loadTasks();
}

function prevPage() {
  if (pagination.page <= 1) return;
  pagination.page -= 1;
  void loadTasks();
}

function nextPage() {
  if (pagination.page >= totalPages.value) return;
  pagination.page += 1;
  void loadTasks();
}

function taskTypeLabel(value?: string) {
  const labels: Record<string, string> = { SAST: "SAST", DAST: "DAST", SCA: "SCA" };
  return labels[String(value || "").toUpperCase()] || value || "-";
}

function statusLabel(value?: string) {
  const labels: Record<string, string> = { PENDING: "排队中", RUNNING: "执行中", SUCCESS: "已完成", FAILED: "失败", TIMEOUT: "超时", CANCELLED: "已取消" };
  return labels[String(value || "").toUpperCase()] || value || "-";
}

function formatTime(value?: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

onMounted(() => {
  void loadTasks();
});
</script>

<style scoped>
.admin-scans-page { display: grid; gap: 16px; }
.admin-scan-hero {
  display: grid;
  grid-template-columns: minmax(320px, 1.15fr) minmax(260px, .62fr) minmax(360px, .9fr);
  gap: 14px;
  align-items: stretch;
  padding: 20px;
  border: 1px solid rgba(7, 89, 133, .22);
  border-radius: 24px;
  color: #082f49;
  background:
    radial-gradient(circle at 18% 10%, rgba(14, 165, 233, .18), transparent 34%),
    linear-gradient(135deg, #f8fafc 0%, #e0f2fe 48%, #cffafe 100%);
  box-shadow: 0 18px 46px rgba(8, 47, 73, .16);
}
.admin-scan-hero .eyebrow { color: #0369a1; }
.admin-scan-hero__intro { display: flex; min-height: 216px; flex-direction: column; justify-content: center; }
.admin-scan-hero h2 { margin: 6px 0 8px; color: #061b33; font-size: clamp(28px, 3vw, 42px); line-height: 1.08; letter-spacing: -.04em; }
.admin-scan-hero p:not(.eyebrow) { max-width: 640px; color: #164e63; font-size: 14px; font-weight: 800; line-height: 1.6; }
.hero-metrics-strip { display: grid; grid-template-columns: repeat(4, minmax(86px, 1fr)); gap: 10px; margin-top: 16px; }
.hero-metrics-strip span { min-height: 58px; border: 1px solid rgba(3, 105, 161, .18); border-radius: 14px; padding: 9px 10px; color: #164e63; background: rgba(255,255,255,.74); font-size: 11px; font-weight: 900; box-shadow: 0 8px 18px rgba(8, 47, 73, .08); }
.hero-metrics-strip b { display: block; color: #061b33; font-size: 22px; line-height: 1; }
.admin-chart-card { min-height: 216px; border: 1px solid rgba(3, 105, 161, .18); border-radius: 20px; padding: 14px; background: rgba(255,255,255,.86); box-shadow: 0 10px 24px rgba(8, 47, 73, .1); }
.chart-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; margin-bottom: 10px; }
.chart-heading strong { color: #061b33; font-size: 16px; }
.chart-heading span { color: #475569; font-size: 12px; font-weight: 900; }
.donut-wrap { display: grid; grid-template-columns: 132px 1fr; gap: 12px; align-items: center; }
.donut-chart { width: 132px; height: 132px; transform: rotate(-90deg); }
.donut-bg { fill: none; stroke: #dbeafe; stroke-width: 6; }
.donut-slice { fill: none; stroke-width: 6; stroke-linecap: butt; }
.donut-chart text { transform: rotate(90deg); transform-origin: 21px 21px; fill: #061b33; font-weight: 900; }
.donut-chart text:first-of-type { font-size: 7px; }
.donut-chart text:last-of-type { fill: #475569; font-size: 3px; }
.chart-legend { display: grid; gap: 8px; }
.chart-legend span { display: flex; align-items: center; gap: 8px; color: #0f172a; font-size: 13px; font-weight: 900; }
.chart-legend i { width: 10px; height: 10px; border-radius: 999px; }
.bar-chart { display: grid; grid-template-columns: repeat(6, 1fr); gap: 9px; align-items: end; height: 162px; }
.bar-chart__item { display: grid; grid-template-rows: 1fr auto auto; gap: 5px; min-width: 0; text-align: center; }
.bar-chart__track { position: relative; height: 96px; border-radius: 999px; background: #e2e8f0; overflow: hidden; }
.bar-chart__track i { position: absolute; inset: auto 0 0; border-radius: inherit; }
.bar-chart__item strong { color: #061b33; font-size: 16px; line-height: 1; }
.bar-chart__item span { color: #334155; font-size: 11px; font-weight: 900; }
.admin-task-panel { color: #0f172a; background: rgba(255,255,255,.96); }
.admin-task-heading { align-items: flex-start; }
.admin-filters { display: grid; grid-template-columns: minmax(260px, 1.4fr) minmax(180px, .7fr) minmax(180px, .7fr) auto; gap: 14px; align-items: end; margin: 18px 0 20px; }
.admin-filter-actions { display: flex; gap: 10px; }
.admin-table-wrap { overflow-x: auto; border: 1px solid rgba(15, 121, 144, .12); border-radius: 22px; }
.admin-task-table { min-width: 1080px; color: #0f172a; }
.admin-task-table th { color: #334155; font-size: 12px; }
.admin-task-table td { vertical-align: middle; }
.user-cell, .task-cell { display: grid; gap: 4px; }
.user-cell strong, .task-cell strong { color: #061b33; }
.user-cell span, .task-cell span { color: #475569; font-size: 12px; font-weight: 700; }
.target-cell { max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.type-pill, .status-pill { display: inline-flex; align-items: center; justify-content: center; min-width: 72px; border-radius: 999px; padding: 8px 10px; font-weight: 900; font-size: 12px; }
.type-pill--sast { background: #e0f2fe; color: #075985; }
.type-pill--dast { background: #dcfce7; color: #166534; }
.type-pill--sca { background: #fef3c7; color: #92400e; }
.status-pill--success { background: #dcfce7; color: #166534; }
.status-pill--running, .status-pill--pending { background: #e0f2fe; color: #075985; }
.status-pill--failed, .status-pill--timeout, .status-pill--cancelled { background: #fee2e2; color: #991b1b; }
.report-link { display: inline-flex; align-items: center; justify-content: center; border-radius: 999px; padding: 9px 14px; color: #fff; background: linear-gradient(135deg, #0f7990, #164e63); font-weight: 900; text-decoration: none; box-shadow: 0 10px 22px rgba(15, 121, 144, .2); }
.admin-pagination { margin-top: 18px; }
.admin-denied h2 { margin: 8px 0; font-size: 34px; }
@media (max-width: 1280px) { .admin-scan-hero { grid-template-columns: 1fr 1fr; } .admin-scan-hero__intro { grid-column: 1 / -1; min-height: auto; } }
@media (max-width: 1100px) { .admin-scan-hero, .admin-filters { grid-template-columns: 1fr; } .donut-wrap { grid-template-columns: 132px 1fr; } }
@media (max-width: 680px) { .admin-scan-hero { padding: 16px; border-radius: 20px; } .hero-metrics-strip, .bar-chart { grid-template-columns: repeat(2, 1fr); } .donut-wrap { grid-template-columns: 1fr; justify-items: center; } .admin-filter-actions { flex-direction: column; } }
</style>
