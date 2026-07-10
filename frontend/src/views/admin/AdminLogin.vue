<template>
  <div class="admin-login-page">
    <!-- 左侧 70%：景区视觉 -->
    <section class="login-visual" aria-hidden="true">
      <img src="/assets/slides/灵山大佛.png" alt="" class="login-bg-img" />
      <div class="login-bg-overlay"></div>
      <div class="login-visual-caption">
        <span class="caption-main">灵山胜境</span>
        <span class="caption-divider">·</span>
        <span class="caption-en">AI Digital Guide</span>
      </div>
    </section>

    <!-- 右侧 30%：登录表单 -->
    <section class="login-panel">
      <div class="login-content">
        <div class="login-accent"></div>
        <h1 class="login-brand">灵山智慧导览</h1>
        <p class="login-subtitle">管理后台</p>
        <div class="login-divider"></div>

        <form @submit.prevent="handleLogin" class="login-form">
          <label class="field-label">管理密码</label>
          <div class="password-wrap">
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="请输入管理密码"
              class="password-input"
              autocomplete="current-password"
            />
            <button type="button" class="eye-toggle" @click="showPassword = !showPassword" tabindex="-1">
              <svg v-if="!showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
            </button>
          </div>

          <p v-if="errorMsg" class="login-error" role="alert" aria-live="polite">{{ errorMsg }}</p>

          <button type="submit" class="login-submit" :disabled="loading">
            <span v-if="loading" class="submit-spinner"></span>
            <span>{{ loading ? '验证中' : '登录' }}</span>
          </button>
        </form>

        <button type="button" class="back-link" @click="goBack">
          <svg viewBox="0 0 20 20" fill="currentColor" class="back-arrow"><path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"/></svg>
          返回首页
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "../../stores/auth";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const password = ref("");
const loading = ref(false);
const errorMsg = ref("");
const showPassword = ref(false);

async function handleLogin() {
  if (loading.value) return;
  if (!password.value) {
    errorMsg.value = "请输入密码";
    return;
  }
  loading.value = true;
  errorMsg.value = "";
  try {
    const ok = authStore.login(password.value);
    if (ok) {
      const redirect = route.query.redirect || "/admin/dashboard";
      router.push(redirect);
    } else {
      errorMsg.value = "密码错误，请重试";
    }
  } finally {
    loading.value = false;
  }
}

function goBack() {
  router.push("/");
}
</script>

<style scoped>
.admin-login-page {
  display: grid;
  grid-template-columns: 7fr 3fr;
  min-height: 100vh;
  background: #0e1115;
}

/* ── 左侧视觉 ── */
.login-visual {
  position: relative;
  overflow: hidden;
}

.login-bg-img {
  width: calc(100% + 8px);
  height: calc(100% + 8px);
  margin: -4px;
  object-fit: cover;
  image-rendering: auto;
  filter: blur(1.5px) brightness(0.95) saturate(1.1);
}

.login-bg-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to right,
    transparent 50%,
    rgba(14, 17, 21, 0.85) 100%
  );
  pointer-events: none;
}

.login-visual-caption {
  position: absolute;
  bottom: 32px;
  left: 32px;
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.caption-main {
  color: rgba(255, 255, 255, 0.85);
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.caption-divider {
  color: rgba(255, 255, 255, 0.3);
}

.caption-en {
  color: rgba(255, 255, 255, 0.45);
  font-size: 14px;
  letter-spacing: 0.06em;
}

/* ── 右侧面板 ── */
.login-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0e1115;
  border-left: 1px solid rgba(255, 255, 255, 0.06);
}

.login-content {
  width: 100%;
  max-width: 340px;
  padding: 48px 32px;
}

.login-accent {
  width: 40px;
  height: 3px;
  border-radius: 2px;
  background: #0065fd;
  margin-bottom: 24px;
}

.login-brand {
  margin: 0 0 8px;
  color: #f0f2f5;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.login-subtitle {
  margin: 0 0 20px;
  color: #7f8d9f;
  font-size: 14px;
}

.login-divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.06);
  margin-bottom: 28px;
}

/* ── 表单 ── */
.login-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-label {
  color: #7f8d9f;
  font-size: 13px;
  font-weight: 500;
}

.password-wrap {
  position: relative;
}

.password-input {
  width: 100%;
  padding: 12px 44px 12px 14px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  color: #f0f2f5;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.password-input::placeholder {
  color: #4a5568;
}

.password-input:focus {
  border-color: #0065fd;
}

.eye-toggle {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #4a5568;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.eye-toggle svg {
  width: 18px;
  height: 18px;
}

.eye-toggle:hover {
  color: #7f8d9f;
}

.login-error {
  margin: 0;
  color: #f56c6c;
  font-size: 13px;
}

.login-submit {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 4px;
  padding: 12px 24px;
  border: none;
  border-radius: 10px;
  background: #0065fd;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, opacity 0.2s;
}

.login-submit:hover {
  background: #0052cc;
}

.login-submit:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.submit-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── 返回链接 ── */
.back-link {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 28px;
  background: none;
  border: none;
  color: #4a5568;
  font-size: 13px;
  cursor: pointer;
  transition: color 0.2s;
  padding: 0;
}

.back-link:hover {
  color: #7f8d9f;
}

.back-arrow {
  width: 14px;
  height: 14px;
}

/* ── 响应式 ── */
@media (max-width: 900px) {
  .admin-login-page {
    grid-template-columns: 1fr;
    grid-template-rows: 35vh 1fr;
  }

  .login-visual {
    order: 1;
  }

  .login-panel {
    order: 2;
    border-left: none;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
  }
}
</style>
