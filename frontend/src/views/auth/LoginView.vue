<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import { useAuthStore } from '@/stores/auth'
import { errorMessage } from '@/shared/api/errors'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const form = reactive({ username: '', password: '' })
const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function submit() {
  if (auth.busy) return
  if (!(await formRef.value?.validate().catch(() => false))) return
  try {
    await auth.login(form)
    ElMessage.success('欢迎回来')
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/')
      ? route.query.redirect
      : '/'
    await router.replace(redirect)
  } catch (error) {
    ElMessage.error(errorMessage(error, '登录失败'))
  }
}
</script>

<template>
  <section class="auth-page page-shell">
    <div class="auth-copy">
      <p class="eyebrow">WELCOME BACK</p>
      <h1>继续你的<br />简单购物旅程</h1>
      <p>登录后可以同步购物车、查看订单，并安全完成支付或取消。</p>
      <div class="auth-note"><span>01</span> 商品浏览无需登录，结算时再回来也不迟。</div>
    </div>
    <div class="auth-card surface-card">
      <div class="card-heading">
        <p class="eyebrow">账户登录</p>
        <h2>很高兴再次见到你</h2>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" size="large" autocomplete="username" placeholder="输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" size="large" type="password" show-password autocomplete="current-password" placeholder="输入密码" />
        </el-form-item>
        <el-button class="submit-button" type="primary" size="large" native-type="submit" :loading="auth.busy">登录</el-button>
      </el-form>
      <p class="switch-copy">还没有账户？<RouterLink :to="{ name: 'register', query: route.query }">立即注册</RouterLink></p>
    </div>
  </section>
</template>

<style scoped>
.auth-page { min-height: calc(100vh - 150px); display: grid; grid-template-columns: 1fr minmax(360px, 470px); align-items: center; gap: clamp(50px, 10vw, 140px); padding-top: 70px; padding-bottom: 60px; }
.auth-copy h1 { margin: 12px 0 24px; font: 500 clamp(48px, 7vw, 86px)/.98 var(--font-display); letter-spacing: -.045em; }
.auth-copy > p:not(.eyebrow) { max-width: 500px; color: var(--muted); font-size: 16px; line-height: 1.9; }
.auth-note { margin-top: 44px; padding-top: 20px; border-top: 1px solid var(--line); color: var(--muted-strong); font-size: 13px; }
.auth-note span { margin-right: 15px; color: var(--accent); font: 600 12px var(--font-display); }
.auth-card { padding: clamp(28px, 5vw, 50px); }
.card-heading { margin-bottom: 30px; }
.card-heading h2 { margin: 8px 0 0; font: 500 28px var(--font-display); }
.submit-button { width: 100%; margin-top: 8px; }
.switch-copy { margin: 24px 0 0; text-align: center; color: var(--muted); font-size: 13px; }
.switch-copy a { color: var(--accent-dark); font-weight: 600; }
@media (max-width: 800px) { .auth-page { grid-template-columns: 1fr; gap: 38px; padding-top: 45px; } .auth-copy h1 { font-size: 48px; } .auth-note { display: none; } }
</style>
