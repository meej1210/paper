<template>
  <section class="panel">
    <h2>创建 SAST 任务</h2>
    <form class="grid" @submit.prevent="submit">
      <label class="field">
        <span>任务名</span>
        <input v-model="taskName" />
      </label>
      <label class="field">
        <span>描述</span>
        <textarea v-model="description" rows="4"></textarea>
      </label>
      <label class="field">
        <span>上传 Python 文件或压缩包</span>
        <input type="file" @change="onFileChange" />
      </label>
      <div class="muted">支持 .py / .zip / .tar.gz，默认上限 20MB</div>
      <div class="error" v-if="errorMessage">{{ errorMessage }}</div>
      <button class="button" type="submit">提交扫描</button>
    </form>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { createSastTask } from "../api/task";

const router = useRouter();
const taskName = ref("");
const description = ref("");
const file = ref<File | null>(null);
const errorMessage = ref("");

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  file.value = target.files?.[0] ?? null;
}

async function submit() {
  errorMessage.value = "";
  if (!file.value) {
    errorMessage.value = "请选择文件";
    return;
  }

  const formData = new FormData();
  formData.append("file", file.value);
  formData.append("task_name", taskName.value);
  formData.append("description", description.value);

  try {
    const response = await createSastTask(formData);
    await router.push(`/tasks/${response.data.task.id}`);
  } catch (error: any) {
    errorMessage.value = error.response?.data?.message || "创建任务失败";
  }
}
</script>