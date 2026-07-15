<template>
  <div class="admin-login-page">
    <header class="login-hero">
      <div>
        <h1>灵山智慧导览</h1>
        <p>管理后台 · 景区 AI 数字人导览系统运营中心</p>
      </div>
      <span class="login-hero-badge"><i></i>安全登录</span>
    </header>

    <section class="login-body">
      <div class="login-card">
        <div class="login-card-head">
          <h2>管理员登录</h2>
          <p>请输入管理密码以访问后台运营面板</p>
        </div>

        <form @submit.prevent="handleLogin" class="login-form">
          <div class="form-group">
            <label class="form-label" for="admin-password">管理密码</label>
            <div class="password-wrap">
              <input
                id="admin-password"
                ref="passwordInputRef"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="请输入管理密码…"
                class="password-input"
                autocomplete="current-password"
                spellcheck="false"
              />
              <button type="button" class="eye-toggle" @click="showPassword = !showPassword" aria-label="切换密码可见性">
                <svg v-if="!showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
              </button>
            </div>
          </div>

          <p v-if="errorMsg" class="login-error" role="alert" aria-live="polite">{{ errorMsg }}</p>

          <button type="submit" class="login-submit" :disabled="loading">
            <span v-if="loading" class="submit-spinner"></span>
            <span>{{ loading ? '验证中…' : '登录管理后台' }}</span>
          </button>
        </form>
      </div>

      <button type="button" class="back-link" @click="goBack">
        <svg viewBox="0 0 20 20" fill="currentColor" class="back-arrow"><path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"/></svg>
        返回游客端首页
      </button>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "../../stores/auth";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const password = ref("");
const loading = ref(false);
const errorMsg = ref("");
const showPassword = ref(false);
const passwordInputRef = ref(null);

onMounted(() => {
  passwordInputRef.value?.focus();
});

async function handleLogin() {
  if (loading.value) return;
  if (!password.value) {
    errorMsg.value = "请输入管理密码";
    return;
  }
  loading.value = true;
  errorMsg.value = "";
  try {
    await authStore.login(password.value);
    const redirect = route.query.redirect || "/admin/dashboard";
    router.push(redirect);
  } catch (err) {
    errorMsg.value = err.message || "密码错误，请重试";
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
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: #fffaf2;
  color: #241d16;
}

.login-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 18px 20px;
  border-bottom: 1px solid #342d26;
  background: linear-gradient(155deg, #241d16 0%, #2e2620 50%, #3a3028 100%);
  box-shadow: 0 2px 6px rgba(23, 18, 14, .12);
}

.login-hero h1 {
  margin: 0;
  color: #fff7eb;
  font-size: clamp(28px, 3vw, 40px);
  font-weight: 700;
  line-height: 1.08;
  letter-spacing: -.03em;
}

.login-hero p {
  max-width: 520px;
  margin: 11px 0 0;
  color: rgba(255, 247, 235, .64);
  font-size: 15px;
  line-height: 1.7;
}

.login-hero-badge {
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid rgba(255, 247, 235, .15);
  border-radius: 2px;
  background: rgba(255, 247, 235, .08);
  color: #fff7eb;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.login-hero-badge i {
  width: 8px;
  height: 8px;
  margin-right: 8px;
  border-radius: 2px;
  background: #44c07a;
  box-shadow: 0 0 6px rgba(68, 192, 122, .55);
}

.login-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 20px;
}

.login-card {
  width: min(420px, 100%);
  border: 1px solid #d4c8b8;
  border-radius: 2px;
  background: #fdf9f2;
  box-shadow: 0 1px 3px rgba(23, 18, 14, .07);
}

.login-card-head {
  padding: 16px 20px;
  border-bottom: 1px solid #e3d9cc;
}

.login-card-head h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -.03em;
  color: #241d16;
}

.login-card-head p {
  margin: 8px 0 0;
  color: #675a4e;
  font-size: 12px;
  line-height: 1.6;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px 20px 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  color: #675a4e;
  font-size: 12px;
  font-weight: 600;
}

.password-wrap {
  position: relative;
}

.password-input {
  width: 100%;
  height: 46px;
  padding: 0 44px 0 14px;
  border: 1px solid #d4c8b8;
  border-radius: 2px;
  background: #fffaf2;
  color: #241d16;
  font-size: 14px;
  font-family: inherit;
  box-sizing: border-box;
  transition: border-color 0.16s ease;
}

.password-input:focus {
  border-color: #248550;
  box-shadow: 0 0 0 2px rgba(36, 133, 80, .12);
  outline: none;
}

.password-input::placeholder {
  color: #b8a898;
}

.eye-toggle {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: none;
  border-radius: 2px;
  background: transparent;
  color: #8c8174;
  cursor: pointer;
  transition: color 0.16s ease;
}

.eye-toggle:hover {
  color: #241d16;
}

.eye-toggle:focus-visible {
  outline: 2px solid #248550;
  outline-offset: 2px;
}

.eye-toggle svg {
  width: 18px;
  height: 18px;
}

.login-error {
  margin: 0;
  padding: 8px 12px;
  border: 1px solid #e3c8c0;
  border-radius: 2px;
  background: #fdf3f0;
  color: #b84c3b;
  font-size: 12px;
  line-height: 1.5;
}

.login-submit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 4px;
  min-height: 42px;
  padding: 0 24px;
  border: 1px solid #248550;
  border-radius: 2px;
  background: #248550;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  letter-spacing: .02em;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(36, 133, 80, .3);
  transition: background .16s ease, box-shadow .16s ease;
}

.login-submit:hover:not(:disabled) {
  background: #1e7043;
  box-shadow: 0 4px 12px rgba(36, 133, 80, .35);
}

.login-submit:focus-visible {
  outline: 2px solid #248550;
  outline-offset: 2px;
}

.login-submit:disabled {
  opacity: .7;
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

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 20px;
  padding: 0;
  border: none;
  border-radius: 2px;
  background: none;
  color: #8c8174;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  transition: color .16s ease;
}

.back-link:hover {
  color: #241d16;
}

.back-link:focus-visible {
  outline: 2px solid #248550;
  outline-offset: 2px;
}

.back-arrow {
  width: 14px;
  height: 14px;
}

@media (max-width: 900px) {
  .login-hero {
    align-items: flex-start;
    flex-direction: column;
    padding: 16px;
  }

  .login-hero p {
    font-size: 13px;
  }

  .login-body {
    padding: 32px 16px;
  }
}

@media (max-width: 640px) {
  .login-card {
    width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .submit-spinner {
    animation: none;
  }
}
</style>
