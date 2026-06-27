<template>
  <section class="login-page">
    <div class="login-card">
      <h2>管理后台登录</h2>
      <p class="login-sub">请输入管理密码以继续</p>
      <el-form @submit.prevent="handleLogin">
        <el-form-item>
          <el-input
            v-model="password"
            type="password"
            placeholder="请输入管理密码"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleLogin" style="width: 100%">
            登录
          </el-button>
        </el-form-item>
      </el-form>
      <p v-if="errorMsg" class="login-error">{{ errorMsg }}</p>
    </div>
  </section>
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

async function handleLogin() {
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
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: 24px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  padding: 40px 36px;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
  text-align: center;
}

.login-card h2 {
  margin: 0 0 6px;
  font-size: 22px;
  color: #0f172a;
}

.login-sub {
  margin: 0 0 24px;
  color: #64748b;
  font-size: 14px;
}

.login-error {
  margin: 12px 0 0;
  color: #dc2626;
  font-size: 13px;
}
</style>
