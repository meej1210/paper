<template>
  <section class="panel">
    <h2>创建 DAST 任务</h2>
    <p class="muted">默认测试目标为本地 Juice Shop；已授权公网目标需后端策略允许并勾选授权确认。</p>
    <form class="grid" @submit.prevent="submit">
      <label class="field">
        <span>任务名称</span>
        <input v-model="form.task_name" placeholder="例如：juice-shop-dast" />
      </label>
      <label class="field">
        <span>目标 URL</span>
        <input v-model="form.target_url" placeholder="http://127.0.0.1:3000 或 https://www.baidu.com/" />
      </label>
      <label class="field">
        <span>超时秒数</span>
        <input v-model.number="form.timeout" type="number" min="1" max="600" />
      </label>
      <label class="field">
        <span>描述</span>
        <textarea v-model="form.description" rows="4" placeholder="仅用于本地靶场或授权测试站点"></textarea>
      </label>
      <label class="authorization-check">
        <span class="checkbox-line">
          <input v-model="form.authorization_confirmed" type="checkbox" />
          <span>我确认该目标属于本地靶场或已获得授权的测试范围，并同意记录授权审计信息</span>
        </span>
      </label>
      <div class="error" v-if="errorMessage">{{ errorMessage }}</div>
      <button class="button" type="submit">提交扫描</button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { createDastTask } from "../api/task";

const router = useRouter();
const errorMessage = ref("");
const form = reactive({
  task_name: "juice-shop-dast",
  target_url: "http://127.0.0.1:3000",
  timeout: 90,
  description: "本地 Juice Shop 动态扫描；百度授权公网示例可填 https://www.baidu.com/",
  authorization_confirmed: false
});

async function submit() {
  errorMessage.value = "";
  if (!form.authorization_confirmed) {
    errorMessage.value = "请先确认该目标属于本地靶场或已获得授权的测试范围";
    return;
  }
  try {
    const response = await createDastTask(form);
    await router.push(`/tasks/${response.data.task.id}`);
  } catch (error: any) {
    errorMessage.value = error.response?.data?.message || "创建任务失败";
  }
}
</script>
