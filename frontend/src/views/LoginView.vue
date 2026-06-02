<template>
  <section class="login-shell">
    <form class="panel login-card" @submit.prevent="submit">
      <div class="login-card__header">
        <h3>登录</h3>
        <p class="muted">输入账号后进入工作台。</p>
      </div>

      <label class="field">
        <span>用户名或邮箱</span>
        <input v-model="form.username" class="field-input" placeholder="请输入用户名或邮箱" />
      </label>

      <label class="field">
        <span>密码</span>
        <input v-model="form.password" type="password" class="field-input" placeholder="请输入密码" />
      </label>

      <div class="error" v-if="errorMessage">{{ errorMessage }}</div>

      <div class="form-actions login-card__actions">
        <button class="button" type="submit" :class="{ 'is-loading': submitting }" :disabled="submitting">{{ submitting ? '登录中...' : '登录' }}</button>
        <RouterLink class="button secondary" to="/register">去注册</RouterLink>
      </div>
    </form>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { login } from "../api/auth";
import { saveToken } from "../store/auth";

const router = useRouter();
const errorMessage = ref("");
const submitting = ref(false);
const form = reactive({ username: "", password: "" });

async function submit() {
  errorMessage.value = "";
  if (!form.username.trim() || !form.password.trim()) {
    errorMessage.value = "请输入用户名和密码";
    return;
  }

  submitting.value = true;
  try {
    const response = await login(form);
    saveToken(response.data.access_token);
    await router.push("/tasks");
  } catch (error: any) {
    errorMessage.value = error.response?.data?.message || "登录失败";
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.login-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px 24px 48px;
}

.login-card {
  display: grid;
  align-content: center;
  gap: 18px;
  width: min(100%, 640px);
  min-height: 0;
  padding: 44px 42px 40px;
  border-radius: 32px;
  box-shadow: 0 28px 64px rgba(19, 34, 56, 0.16);
}

.login-card__header {
  display: grid;
  gap: 12px;
}

.login-card__header h3 {
  margin: 0;
  font-size: clamp(40px, 5vw, 46px);
  color: #17324d;
}

.login-card__header .muted {
  margin: 0;
  font-size: 18px;
  line-height: 1.65;
}

.field {
  gap: 10px;
}

.field span {
  font-size: 22px;
  font-weight: 700;
}

.field-input {
  min-height: 68px;
  padding: 0 24px;
  border-radius: 22px;
  font-size: 22px;
}

.error {
  font-size: 16px;
  border-radius: 16px;
}

.form-actions {
  margin-top: 6px;
}

.login-card__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}

.login-card__actions > * {
  justify-content: center;
  min-height: 64px;
  border-radius: 999px;
  font-size: 24px;
  font-weight: 700;
}

@media (max-width: 960px) {
  .login-card {
    width: min(100%, 600px);
    padding: 38px 30px 34px;
  }
}

@media (max-width: 640px) {
  .login-shell {
    min-height: auto;
    padding: 20px 14px 32px;
  }

  .login-card {
    min-height: auto;
    padding: 28px 20px;
    border-radius: 24px;
  }

  .login-card__header h3 {
    font-size: 38px;
  }

  .login-card__header .muted,
  .field span,
  .field-input,
  .login-card__actions > * {
    font-size: 20px;
  }

  .field-input,
  .login-card__actions > * {
    min-height: 62px;
  }

  .login-card__actions {
    grid-template-columns: 1fr;
  }
}
</style>
