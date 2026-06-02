<template>
  <section class="auth-layout">
    <div class="panel panel--hero auth-hero">
      <div class="auth-hero__content">
        <div>
          <p class="eyebrow">Create Account</p>
          <h3>注册后即可进入统一安全工作台</h3>
          <p class="muted">注册完成后，你可以直接体验静态审计、动态扫描、任务详情和报告导出流程。</p>
        </div>
        <div class="auth-hero__highlights">
          <span class="visual-pill">统一身份入口</span>
          <span class="visual-pill">任务可追踪</span>
          <span class="visual-pill">审计链路清晰</span>
        </div>
        <ul class="insight-list insight-list--tight">
          <li>建议使用易识别的用户名，便于审计日志和任务归属展示。</li>
          <li>注册成功后会跳转登录页，随后即可进入工作台。</li>
          <li>如果你是演示账号，也建议填真实可辨识的邮箱。</li>
        </ul>
      </div>

      <figure class="hero-illustration hero-illustration--auth">
        <img :src="loginIllustration" alt="平台注册与访问控制插画" />
      </figure>
    </div>

    <form class="panel auth-card" @submit.prevent="submit">
      <div class="section-heading">
        <div>
          <h3>注册账号</h3>
          <p class="muted">创建一个用于任务提交和审计追踪的账号。</p>
        </div>
      </div>

      <label class="field">
        <span>用户名</span>
        <input v-model="form.username" class="field-input" />
      </label>

      <label class="field">
        <span>邮箱</span>
        <input v-model="form.email" type="email" class="field-input" />
      </label>

      <label class="field">
        <span>密码</span>
        <input v-model="form.password" type="password" class="field-input" />
      </label>

      <div class="error" v-if="errorMessage">{{ errorMessage }}</div>

      <div class="form-actions">
        <button class="button" type="submit" :class="{ 'is-loading': submitting }" :disabled="submitting">{{ submitting ? '注册中...' : '注册' }}</button>
        <RouterLink class="button secondary" to="/login">返回登录</RouterLink>
      </div>
    </form>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { register } from "../api/auth";
import loginIllustration from "../assets/illustrations/login-illustration.svg";

const router = useRouter();
const errorMessage = ref("");
const submitting = ref(false);
const form = reactive({ username: "", email: "", password: "" });

async function submit() {
  errorMessage.value = "";
  if (!form.username.trim()) {
    errorMessage.value = "请输入用户名";
    return;
  }
  if (!form.email.includes("@")) {
    errorMessage.value = "请输入有效邮箱";
    return;
  }
  if (form.password.length < 6) {
    errorMessage.value = "密码至少 6 位";
    return;
  }

  submitting.value = true;
  try {
    await register(form);
    await router.push("/login");
  } catch (error: any) {
    errorMessage.value = error.response?.data?.message || "注册失败";
  } finally {
    submitting.value = false;
  }
}
</script>
