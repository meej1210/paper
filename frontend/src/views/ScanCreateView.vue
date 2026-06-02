<template>
  <section class="scan-create">
    <div class="panel panel--hero scan-create__hero">
      <div>
        <p class="eyebrow">New Scan</p>
        <h2>统一新建扫描</h2>
        <p class="scan-create__lead">先选扫描方式，再补齐必要信息。创建成功后会直接带你进入任务详情页。</p>
      </div>
      <div class="toggle-group">
        <button type="button" class="toggle-group__button" :class="{ 'is-active': activeType === 'sast' }" @click="setActiveType('sast')">SAST</button>
        <button type="button" class="toggle-group__button" :class="{ 'is-active': activeType === 'sca' }" @click="setActiveType('sca')">SCA</button>
        <button type="button" class="toggle-group__button" :class="{ 'is-active': activeType === 'dast' }" @click="setActiveType('dast')">DAST</button>
      </div>
    </div>

    <div class="scan-create__grid">
      <form class="panel scan-form" @submit.prevent="submit">
        <div class="section-heading">
          <div>
            <h3>{{ formTitle }}</h3>
            <p class="muted">{{ activeTypeDescription }}</p>
          </div>
          <span class="scan-badge">{{ activeType.toUpperCase() }}</span>
        </div>

        <div class="form-section">
          <h4>基础信息</h4>
          <div class="grid two">
            <label class="field">
              <span>任务名称</span>
              <input v-if="activeType === 'sast'" v-model="sastForm.task_name" class="field-input" placeholder="例如：core-service-sast" />
              <input v-else-if="activeType === 'sca'" v-model="scaForm.task_name" class="field-input" placeholder="例如：requirements-sca" />
              <input v-else v-model="dastForm.task_name" class="field-input" placeholder="例如：juice-shop-dast" />
            </label>
            <label class="field" v-if="activeType === 'dast'">
              <span>超时时间（秒）</span>
              <input v-model.number="dastForm.timeout" type="number" min="10" max="600" class="field-input" />
            </label>
          </div>

          <label class="field">
            <span>任务说明</span>
            <textarea v-if="activeType === 'sast'" v-model="sastForm.description" rows="4" class="field-input" placeholder="说明扫描范围、代码包来源或本次关注点"></textarea>
            <textarea v-else-if="activeType === 'sca'" v-model="scaForm.description" rows="4" class="field-input" placeholder="说明依赖清单来源、版本范围或本次关注的修复目标"></textarea>
            <textarea v-else v-model="dastForm.description" rows="4" class="field-input" placeholder="说明测试范围、授权状态或本次验证重点"></textarea>
          </label>
        </div>

        <div class="form-section" v-if="activeType === 'sast'">
          <h4>扫描配置</h4>
          <div class="grid two">
            <label class="field">
              <span>扫描引擎</span>
              <select v-model="sastForm.scanner_engine" class="field-input">
                <option v-for="option in sastEngineOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
              </select>
            </label>
            <div class="callout callout--soft">
              <strong>{{ selectedEngineMeta.title }}</strong>
              <p>{{ selectedEngineMeta.description }}</p>
            </div>
          </div>

          <h4>扫描目标</h4>
          <label class="upload-box">
            <input type="file" class="upload-box__input" @change="onFileChange" />
            <span class="upload-box__title">上传代码文件或压缩包</span>
            <span class="upload-box__hint">{{ selectedEngineMeta.hint }}</span>
            <strong>{{ selectedFile ? `${selectedFile.name} (${formatFileSize(selectedFile.size)})` : '点击选择文件' }}</strong>
          </label>
        </div>

        <div class="form-section" v-else-if="activeType === 'sca'">
          <h4>依赖清单</h4>
          <label class="upload-box">
            <input type="file" class="upload-box__input" accept=".txt,.zip" @change="onFileChange" />
            <span class="upload-box__title">上传 requirements.txt 或项目 ZIP</span>
            <span class="upload-box__hint">SCA 会从 Python requirements 依赖清单中识别已知漏洞与可修复版本。</span>
            <strong>{{ selectedFile ? `${selectedFile.name} (${formatFileSize(selectedFile.size)})` : '点击选择依赖文件' }}</strong>
          </label>
        </div>

        <div class="form-section" v-else>
          <h4>目标配置</h4>
          <div class="grid two">
            <label class="field">
              <span>目标 URL</span>
              <input v-model="dastForm.target_url" class="field-input" placeholder="http://127.0.0.1:3000" />
            </label>
            <div class="callout callout--soft">
              <strong>靶场预设</strong>
              <p>选择本地靶场或已授权公网目标会自动填入目标地址、任务名和推荐超时时间。</p>
              <select v-model="selectedDastPreset" class="field-input" @change="applySelectedDastPreset">
                <option v-for="preset in dastTargetPresets" :key="preset.key" :value="preset.key">{{ preset.name }}</option>
              </select>
            </div>
          </div>
          <div class="callout callout--warning">
            <strong>测试提醒</strong>
            <p>DAST 仅用于你已获得授权的测试目标，避免对非授权站点执行动态扫描。</p>
          </div>
          <div class="callout callout--soft" v-if="isPublicDastTarget">
            <strong>授权公网扫描模式</strong>
            <p>公网目标需要后端开启 DAST_ALLOW_PUBLIC_TARGETS 或命中 DAST_ALLOWED_HOSTS，并会使用更短超时和低强度扫描参数。</p>
          </div>
          <label class="authorization-check">
            <span class="checkbox-line">
              <input v-model="dastForm.authorization_confirmed" type="checkbox" />
              <span>我确认该目标属于本地靶场或已获得授权的测试范围，并同意记录授权审计信息</span>
            </span>
          </label>
        </div>

        <div class="form-section">
          <h4>提交确认</h4>
          <div class="confirm-grid">
            <div class="confirm-item">
              <span class="muted">扫描类型</span>
              <strong>{{ activeType.toUpperCase() }}</strong>
            </div>
            <div class="confirm-item">
              <span class="muted">目标摘要</span>
              <strong>{{ targetSummary }}</strong>
            </div>
            <div class="confirm-item" v-if="activeType === 'sast'">
              <span class="muted">SAST 引擎</span>
              <strong>{{ selectedEngineMeta.label }}</strong>
            </div>
          </div>
        </div>

        <div class="error" v-if="errorMessage">{{ errorMessage }}</div>
        <div class="success" v-if="successMessage">{{ successMessage }}</div>

        <div class="form-actions">
          <button class="button" type="submit" :class="{ 'is-loading': submitting }" :disabled="submitting">{{ submitLabel }}</button>
          <RouterLink class="button secondary" to="/tasks">返回工作台</RouterLink>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { createDastTask, createSastTask, createScaTask } from "../api/task";

type ScanType = "sast" | "dast" | "sca";
type SastScannerEngine = "bandit" | "semgrep";

const router = useRouter();
const route = useRoute();
const activeType = ref<ScanType>(resolveScanType(route.query.type));
const selectedFile = ref<File | null>(null);
const errorMessage = ref("");
const successMessage = ref("");
const submitting = ref(false);
const selectedDastPreset = ref("juice-shop");
const sastEngineOptions: Array<{ value: SastScannerEngine; label: string; title: string; description: string; hint: string }> = [
  {
    value: "bandit",
    label: "Bandit",
    title: "Bandit：Python 定向审计",
    description: "适合传统 Python 安全问题审计，结果风格稳定，适合和当前历史演示保持一致。",
    hint: "支持 `.py`、`.zip`、`.tar.gz`，当前更适合 Python 代码包。"
  },
  {
    value: "semgrep",
    label: "Semgrep",
    title: "Semgrep：规则驱动扫描",
    description: "适合扩展平台能力边界。当前后端默认接入 `p/python` 规则集，重点展示规则命中、CWE/OWASP 映射和代码片段。",
    hint: "支持 `.py`、`.zip`、`.tar.gz`，当前默认使用 Python 规则集 `p/python`。"
  }
];
const sastForm = reactive({
  task_name: "",
  description: "",
  scanner_engine: "bandit" as SastScannerEngine
});
const scaForm = reactive({
  task_name: "requirements-sca",
  description: "Python 依赖漏洞扫描"
});
const dastTargetPresets = [
  {
    key: "juice-shop",
    name: "Juice Shop（本地 3000）",
    task_name: "juice-shop-dast",
    target_url: "http://127.0.0.1:3000",
    timeout: 90,
    description: "本地 Juice Shop 动态扫描"
  },
  {
    key: "juice-shop-fallback",
    name: "Juice Shop fallback（本地 3100）",
    task_name: "juice-shop-fallback-dast",
    target_url: "http://127.0.0.1:3100",
    timeout: 90,
    description: "本地 Juice Shop fallback 动态扫描"
  },
  {
    key: "dvwa",
    name: "DVWA（本地 3001）",
    task_name: "dvwa-dast",
    target_url: "http://127.0.0.1:3001",
    timeout: 120,
    description: "本地 DVWA 传统 Web 漏洞扫描"
  },
  {
    key: "webgoat",
    name: "WebGoat（本地 3002）",
    task_name: "webgoat-dast",
    target_url: "http://127.0.0.1:3002/WebGoat",
    timeout: 180,
    description: "本地 WebGoat 训练靶场扫描"
  },
  {
    key: "mutillidae",
    name: "Mutillidae II（本地 3003）",
    task_name: "mutillidae-dast",
    target_url: "http://127.0.0.1:3003",
    timeout: 120,
    description: "本地 Mutillidae II 综合靶场扫描"
  },
  {
    key: "baidu",
    name: "百度（授权公网）",
    task_name: "baidu-authorized-dast",
    target_url: "https://www.baidu.com/",
    timeout: 60,
    description: "已授权公网目标百度低强度动态扫描"
  },
  {
    key: "custom",
    name: "自定义授权 URL",
    task_name: "authorized-url-dast",
    target_url: "",
    timeout: 120,
    description: "已获得授权的自定义目标"
  }
];
const dastForm = reactive({
  task_name: "juice-shop-dast",
  target_url: "http://127.0.0.1:3000",
  timeout: 90,
  description: "本地 Juice Shop 动态扫描",
  authorization_confirmed: false
});

const formTitle = computed(() => {
  if (activeType.value === "sast") return "静态审计配置";
  if (activeType.value === "sca") return "依赖扫描配置";
  return "动态扫描配置";
});
const activeTypeDescription = computed(() => {
  if (activeType.value === "sast") return "上传代码包发起静态安全审计，适合快速查看规则命中、高危问题和重点文件。";
  if (activeType.value === "sca") return "上传 requirements.txt 或项目 ZIP 发起依赖漏洞扫描，适合展示组件风险和可修复版本。";
  return "输入目标地址发起动态扫描，适合检查运行态漏洞、配置缺口和请求证据。";
});
const selectedEngineMeta = computed(() => (
  sastEngineOptions.find((option) => option.value === sastForm.scanner_engine) ?? sastEngineOptions[0]
));
const submitLabel = computed(() => {
  if (submitting.value) return "正在创建任务...";
  if (activeType.value === "sca") return "创建 SCA 任务";
  return activeType.value === "sast" ? "创建 SAST 任务" : "创建 DAST 任务";
});
const targetSummary = computed(() => {
  if (activeType.value === "dast") return dastForm.target_url;
  return selectedFile.value?.name || "等待上传文件";
});
const isPublicDastTarget = computed(() => {
  if (activeType.value !== "dast") return false;
  try {
    const url = new URL(dastForm.target_url);
    return !["localhost", "127.0.0.1", "::1"].includes(url.hostname);
  } catch {
    return false;
  }
});

watch(() => route.query.type, (value) => {
  activeType.value = resolveScanType(value);
});

function resolveScanType(value: unknown): ScanType {
  if (value === "dast") return "dast";
  if (value === "sca") return "sca";
  return "sast";
}

function setActiveType(type: ScanType) {
  activeType.value = type;
  router.replace({ query: { ...route.query, type } });
}

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  selectedFile.value = target.files?.[0] ?? null;
}

function applySelectedDastPreset() {
  const preset = dastTargetPresets.find((item) => item.key === selectedDastPreset.value);
  if (!preset) return;
  dastForm.task_name = preset.task_name;
  dastForm.target_url = preset.target_url;
  dastForm.timeout = preset.timeout;
  dastForm.description = preset.description;
}

function formatFileSize(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

async function submit() {
  errorMessage.value = "";
  successMessage.value = "";
  submitting.value = true;

  try {
    if (activeType.value === "sast") {
      if (!selectedFile.value) {
        throw new Error("请先上传待审计的代码文件或压缩包");
      }
      const formData = new FormData();
      formData.append("file", selectedFile.value);
      formData.append("task_name", sastForm.task_name);
      formData.append("description", sastForm.description);
      formData.append("scanner_engine", sastForm.scanner_engine);
      const response = await createSastTask(formData);
      successMessage.value = "任务已创建，正在进入详情页...";
      await new Promise((resolve) => window.setTimeout(resolve, 260));
      await router.push({ name: "task-detail", params: { id: response.data.task.id }, query: { type: "SAST" } });
      return;
    }

    if (activeType.value === "sca") {
      if (!selectedFile.value) {
        throw new Error("请先上传 requirements.txt 或包含 requirements.txt 的 ZIP");
      }
      const formData = new FormData();
      formData.append("file", selectedFile.value);
      formData.append("task_name", scaForm.task_name);
      formData.append("description", scaForm.description);
      const response = await createScaTask(formData);
      successMessage.value = "任务已创建，正在进入详情页...";
      await new Promise((resolve) => window.setTimeout(resolve, 260));
      await router.push({ name: "task-detail", params: { id: response.data.task.id }, query: { type: "SCA" } });
      return;
    }

    if (!dastForm.authorization_confirmed) {
      throw new Error("Please confirm the DAST target is local or explicitly authorized before submitting");
    }
    const response = await createDastTask(dastForm);
    successMessage.value = "任务已创建，正在进入详情页...";
    await new Promise((resolve) => window.setTimeout(resolve, 260));
    await router.push({ name: "task-detail", params: { id: response.data.task.id }, query: { type: "DAST" } });
  } catch (error: any) {
    errorMessage.value = error.response?.data?.message || error.message || "创建任务失败";
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.authorization-check {
  border: 1px solid rgba(245, 158, 11, 0.28);
  border-radius: 18px;
  padding: 14px;
  background: rgba(245, 158, 11, 0.08);
}
.checkbox-line {
  display: flex;
  gap: 10px;
  align-items: center;
  margin: 8px 0;
}
.checkbox-line input {
  width: 18px;
  height: 18px;
}
</style>
