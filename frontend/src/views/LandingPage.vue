<template>
  <div class="landing-page">
    <header class="landing-header">
      <h1>灵山智慧导览系统</h1>
      <p>Lingshan Smart Guide System</p>
    </header>

    <div class="entry-cards">
      <button type="button" class="entry-card tourist-card" @click="enterTourist">
        <span class="card-icon">👥</span>
        <h2>游客端</h2>
        <p>与数字人导游互动</p>
        <ul class="card-features">
          <li>语音问答</li>
          <li>拍照识景</li>
          <li>路线规划</li>
        </ul>
        <span class="entry-button">进入游览</span>
      </button>

      <button type="button" class="entry-card admin-card" @click="enterAdmin">
        <span class="card-icon">🔧</span>
        <h2>管理后台</h2>
        <p>知识库管理与优化</p>
        <ul class="card-features">
          <li>盲区标注</li>
          <li>数据分析</li>
          <li>反馈处理</li>
        </ul>
        <span class="entry-button">进入管理</span>
      </button>
    </div>

    <footer class="landing-footer">
      <p>灵山胜境景区 © 2026 | 软件杯参赛作品</p>
    </footer>
  </div>
</template>

<script setup>
import { useRouter } from "vue-router";

const router = useRouter();

function enterTourist() {
  router.push("/tourist/welcome");
}

function enterAdmin() {
  router.push("/admin/dashboard");
}
</script>

<style scoped>
.landing-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background:
    radial-gradient(circle at 20% 30%, rgba(184, 137, 79, 0.15), transparent 40%),
    radial-gradient(circle at 80% 70%, rgba(102, 128, 107, 0.12), transparent 40%),
    linear-gradient(180deg, var(--lingshan-paper) 0%, #f3efe6 100%);
}

.landing-header {
  text-align: center;
  margin-bottom: 36px;
}

.landing-header h1 {
  margin: 0 0 8px;
  color: var(--lingshan-ink);
  font-family: "STKaiti", "KaiTi", "FangSong", serif;
  font-size: 36px;
  font-weight: 600;
  letter-spacing: 0.12em;
}

.landing-header p {
  margin: 0;
  color: var(--lingshan-stone);
  font-family: Georgia, serif;
  font-size: 16px;
  letter-spacing: 0.08em;
}

.entry-cards {
  display: grid;
  grid-template-columns: repeat(2, 320px);
  gap: 32px;
  margin-bottom: 36px;
}

.entry-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 28px;
  border: 2px solid var(--lingshan-line);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 12px 40px rgba(57, 70, 58, 0.08);
  cursor: pointer;
  transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
  text-align: center;
}

.entry-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 20px 60px rgba(57, 70, 58, 0.15);
}

.tourist-card:hover {
  border-color: var(--lingshan-green);
}

.admin-card:hover {
  border-color: var(--lingshan-gold);
}

.card-icon {
  font-size: 52px;
  margin-bottom: 16px;
}

.entry-card h2 {
  margin: 0 0 8px;
  color: var(--lingshan-ink);
  font-size: 24px;
  font-weight: 600;
}

.entry-card p {
  margin: 0 0 14px;
  color: var(--lingshan-stone);
  font-size: 15px;
}

.card-features {
  list-style: none;
  padding: 0;
  margin: 0 0 20px;
  text-align: center;
}

.card-features li {
  margin: 6px 0;
  color: var(--lingshan-stone);
  font-size: 13px;
}

.card-features li::before {
  content: "· ";
  color: var(--lingshan-green);
  font-weight: 700;
}

.entry-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 28px;
  border: 2px solid var(--lingshan-green);
  border-radius: 999px;
  background: var(--lingshan-green);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  transition: background 0.2s ease, transform 0.2s ease;
}

.admin-card .entry-button {
  border-color: var(--lingshan-gold);
  background: var(--lingshan-gold);
}

.entry-card:hover .entry-button {
  transform: scale(1.05);
}

.landing-footer {
  color: var(--lingshan-stone);
  font-size: 13px;
  text-align: center;
}

.landing-footer p {
  margin: 0;
}

@media (max-width: 900px) {
  .entry-cards {
    grid-template-columns: 1fr;
    gap: 24px;
    max-width: 400px;
  }

  .landing-header h1 {
    font-size: 32px;
  }
}
</style>
