<template>
  <section class="workspace-grid">
    <div class="panel panel--hero workspace-hero">
      <div class="workspace-hero__main">
        <div>
          <p class="eyebrow">安全工作区</p>
          <h2>任务工作台</h2>
          <p class="workspace-hero__lead">集中查看任务状态，直接进入报告和处理流程。</p>
        </div>

        <div class="workspace-hero__actions">
          <RouterLink class="button" to="/scan/new?type=sast">新建静态审计</RouterLink>
          <RouterLink class="button secondary" to="/scan/new?type=sca">新建依赖审计</RouterLink>
          <RouterLink class="button secondary" to="/scan/new?type=dast">新建动态扫描</RouterLink>
          <button class="button ghost" :class="{ 'is-loading': loading || summaryLoading }" @click="refreshAll" :disabled="loading || summaryLoading">刷新状态</button>
        </div>
      </div>

      <div class="workspace-hero__aside">
        <div class="workspace-stats">
          <article v-for="card in summaryCards" :key="card.label" class="workspace-stat">
            <span class="muted">{{ card.label }}</span>
            <strong>{{ card.value }}</strong>
            <small>{{ card.hint }}</small>
          </article>
        </div>
      </div>
    </div>

    <div class="panel workspace-panel">
      <div class="section-heading">
        <div>
          <h3>任务队列</h3>
          <p class="muted">展示最近创建的任务，可直接进入详情继续处理。</p>
        </div>
        <div class="muted">第 {{ pagination.page }} 页 / 共 {{ totalPages }} 页，合计 {{ pagination.total }} 条</div>
      </div>

      <div class="error" v-if="errorMessage">{{ errorMessage }}</div>

      <div v-else-if="loading" class="empty-state loading-state">
        <h4>正在同步任务状态</h4>
        <p>稍等片刻，工作台正在拉取最新任务列表。</p>
      </div>

      <template v-else-if="tasks.length">
        <table class="table">
          <thead>
            <tr>
              <th>编号</th>
              <th>类型</th>
              <th>任务名称</th>
              <th>状态</th>
              <th>结果摘要</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in tasks" :key="task.id" class="table-row-clickable" @click="openTask(task)">
              <td><strong>#{{ task.user_task_no || task.id }}</strong></td>
              <td>
                <div class="task-kind-badges">
                  <span class="task-kind-badge" :class="taskTypeClass(task.task_type)">
                    {{ taskTypeLabel(task.task_type) }}
                  </span>
                  <span v-if="task.task_type === 'SAST' && task.scanner_engine" class="task-kind-badge task-kind-badge--engine">
                    {{ formatScannerEngine(task.scanner_engine) }}
                  </span>
                </div>
              </td>
              <td>
                <div class="table-primary">{{ task.task_name || "未命名任务" }}</div>
                <div class="muted">{{ formatDuration(task.duration_ms) }}</div>
              </td>
              <td><TaskStatusTag :status="task.status" /></td>
              <td>{{ task.result_summary || defaultSummary(task) }}</td>
              <td>{{ formatDate(task.created_at) }}</td>
              <td>
                <button class="button secondary button--small" type="button" @click.stop="openTask(task)">
                  {{ taskActionLabel(task) }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>

        <div class="toolbar" style="margin-top: 20px; margin-bottom: 0;">
          <div class="muted">当前展示 {{ tasks.length }} 条任务</div>
          <div class="nav">
            <button class="button secondary button--small" @click="prevPage" :disabled="pagination.page <= 1 || loading">上一页</button>
            <button class="button secondary button--small" @click="nextPage" :disabled="pagination.page >= totalPages || loading">下一页</button>
          </div>
        </div>
      </template>

      <div v-else class="empty-state">
        <h4>还没有创建任何扫描任务</h4>
        <p>从统一的新建扫描页发起第一条任务，后续状态和报告都会在这里汇总。</p>
        <RouterLink class="button" to="/scan/new">去创建第一条扫描任务</RouterLink>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { getTaskSummary, listTasks } from "../api/task";
import TaskStatusTag from "../components/TaskStatusTag.vue";
import type { Task } from "../types/task";

const router = useRouter();
const tasks = ref<Task[]>([]);
const taskSummary = ref<any>(null);
const errorMessage = ref("");
const loading = ref(false);
const summaryLoading = ref(false);
const pagination = reactive({
  page: 1,
  page_size: 8,
  total: 0
});

const totalPages = computed(() => Math.max(1, Math.ceil(pagination.total / pagination.page_size)));
const summaryCards = computed(() => {
  const summary = taskSummary.value;
  return [
    { label: "任务总数", value: summary?.totals ?? 0, hint: "来自任务统计接口" },
    { label: "进行中", value: (summary?.running_count ?? 0) + (summary?.pending_count ?? 0), hint: "执行中 + 排队中" },
    { label: "已完成", value: summary?.success_count ?? 0, hint: "可查看报告" },
    { label: "需复核", value: summary?.failed_count ?? 0, hint: "失败、超时、已取消" }
  ];
});

async function loadTasks() {
  loading.value = true;
  errorMessage.value = "";
  try {
    const response = await listTasks({
      page: pagination.page,
      page_size: pagination.page_size
    });
    tasks.value = response.data.items;
    pagination.total = response.data.pagination.total;
  } catch (error: any) {
    tasks.value = [];
    pagination.total = 0;
    errorMessage.value = error.response?.data?.message || "加载任务失败";
  } finally {
    loading.value = false;
  }
}

async function loadSummary() {
  summaryLoading.value = true;
  try {
    const response = await getTaskSummary();
    taskSummary.value = response.data;
  } catch {
    taskSummary.value = null;
  } finally {
    summaryLoading.value = false;
  }
}

function openTask(task: Task) {
  router.push({ name: "task-detail", params: { id: task.id }, query: { type: task.task_type } });
}

function defaultSummary(task: Task) {
  if (task.status === "RUNNING" || task.status === "PENDING") return "任务仍在执行中，可进入详情查看最新状态。";
  if (task.status === "SUCCESS") return "任务已完成，可查看报告和导出结果。";
  return "任务需要复核执行结果或重新提交。";
}

function taskActionLabel(task: Task) {
  if (task.status === "SUCCESS") return "查看报告";
  if (task.status === "RUNNING" || task.status === "PENDING") return "查看进度";
  return "继续处理";
}

function formatScannerEngine(engine?: Task["scanner_engine"]) {
  if (engine === "semgrep") return "Semgrep";
  if (engine === "bandit") return "Bandit";
  return "-";
}

function taskTypeClass(taskType: Task["task_type"]) {
  if (taskType === "SAST") return "task-kind-badge--sast";
  if (taskType === "SCA") return "task-kind-badge--engine";
  return "task-kind-badge--dast";
}

function taskTypeLabel(taskType: Task["task_type"]) {
  if (taskType === "SAST") return "静态审计";
  if (taskType === "SCA") return "依赖审计";
  if (taskType === "DAST") return "动态扫描";
  return taskType;
}

function formatDate(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { timeZone: "Asia/Shanghai", hour12: false });
}

function formatDuration(duration?: number | null) {
  if (!duration) return "尚未完成";
  if (duration < 1000) return `${duration} ms`;
  return `${(duration / 1000).toFixed(2)} s`;
}

function prevPage() {
  if (pagination.page > 1) {
    pagination.page -= 1;
    void loadTasks();
  }
}

function nextPage() {
  if (pagination.page < totalPages.value) {
    pagination.page += 1;
    void loadTasks();
  }
}

function refreshAll() {
  void Promise.all([loadTasks(), loadSummary()]);
}

onMounted(() => {
  refreshAll();
});
</script>
