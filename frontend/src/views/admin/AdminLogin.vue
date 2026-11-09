<template>
  <div class="admin-login-page">
    <header class="login-hero">
      <div>
        <h1>灵山胜境</h1>
        <p>景区运营工作台</p>
      </div>
    </header>

    <section class="login-body">
      <div class="login-card">
        <div class="login-card-head">
          <h2>管理员登录</h2>
          <p>使用管理密码继续</p>
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
  background: #f5f6f4;
  color: #202723;
}

.login-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 28px;
  border-bottom: 1px solid #dce2dd;
  background: #fff;
}

.login-hero h1 {
  margin: 0;
  color: #202723;
  font-size: 17px;
  font-weight: 600;
  line-height: 1.4;
  letter-spacing: 0;
}

.login-hero p {
  margin: 3px 0 0;
  color: #59645d;
  font-size: 12px;
  line-height: 1.5;
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
  border: 1px solid #dce2dd;
  border-radius: 6px;
  background: #fff;
  box-shadow: none;
}

.login-card-head {
  padding: 16px 20px;
  border-bottom: 1px solid #dce2dd;
}

.login-card-head h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -.03em;
  color: #202723;
}

.login-card-head p {
  margin: 8px 0 0;
  color: #59645d;
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
  color: #59645d;
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
  border: 1px solid #dce2dd;
  border-radius: 5px;
  background: #fff;
  color: #202723;
  font-size: 14px;
  font-family: inherit;
  box-sizing: border-box;
  transition: border-color 0.16s ease;
}

.password-input:focus {
  border-color: #285a46;
  box-shadow: 0 0 0 2px rgba(40, 90, 70, .12);
  outline: none;
}

.password-input::placeholder {
  color: #7b857e;
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
  color: #59645d;
  cursor: pointer;
  transition: color 0.16s ease;
}

.eye-toggle:hover {
  color: #202723;
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
  border: 1px solid #e4c8c1;
  border-radius: 5px;
  background: #fff5f2;
  color: #9b3325;
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
  border: 1px solid #285a46;
  border-radius: 5px;
  background: #285a46;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  letter-spacing: .02em;
  cursor: pointer;
  box-shadow: none;
  transition: background .16s ease;
}

.login-submit:hover:not(:disabled) {
  background: #204a39;
}

.login-submit:focus-visible {
  outline: 2px solid #285a46;
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
  color: #59645d;
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  transition: color .16s ease;
}

.back-link:hover {
  color: #202723;
}

.back-link:focus-visible {
  outline: 2px solid #285a46;
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

  .password-input {
    font-size: 16px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .submit-spinner {
    animation: none;
  }
}
</style>
