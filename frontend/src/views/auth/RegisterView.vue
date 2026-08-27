<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import { useAuthStore } from '@/stores/auth'
import { ApiError, errorMessage } from '@/shared/api/errors'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const formRef = ref<FormInstance>()
const form = reactive({ username: '', email: '', phone: '', password: '', password_confirm: '' })
const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少 8 位', trigger: 'blur' },
  ],
  password_confirm: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: (_rule, value, callback) => value === form.password ? callback() : callback(new Error('两次密码不一致')), trigger: 'blur' },
  ],
}

async function submit() {
  if (auth.busy) return
  if (!(await formRef.value?.validate().catch(() => false))) return
  try {
    await auth.register(form)
    ElMessage.success('注册成功，欢迎加入')
    const redirect = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') ? route.query.redirect : '/'
    await router.replace(redirect)
  } catch (error) {
    if (error instanceof ApiError) {
      const fields = error.fieldErrors
      for (const field of ['username', 'email', 'phone', 'password', 'password_confirm']) {
        const message = fields[field]?.[0]
        if (message) {
          formRef.value?.scrollToField(field)
          ElMessage.error(message)
          return
        }
      }
    }
    ElMessage.error(errorMessage(error, '注册失败'))
  }
}
</script>

<template>
  <section class="register-page page-shell">
    <div class="register-card surface-card">
      <header>
        <p class="eyebrow">JOIN MINI MALL</p>
        <h1>创建你的账户</h1>
        <p>只需几项基本信息，随后即可保存购物车并完成订单。</p>
      </header>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="submit">
        <div class="form-grid">
          <el-form-item label="用户名" prop="username"><el-input v-model="form.username" size="large" autocomplete="username" /></el-form-item>
          <el-form-item label="邮箱（选填）" prop="email"><el-input v-model="form.email" size="large" autocomplete="email" /></el-form-item>
          <el-form-item label="手机（选填）" prop="phone"><el-input v-model="form.phone" size="large" autocomplete="tel" /></el-form-item>
          <span class="desktop-spacer" />
          <el-form-item label="密码" prop="password"><el-input v-model="form.password" size="large" type="password" show-password autocomplete="new-password" /></el-form-item>
          <el-form-item label="确认密码" prop="password_confirm"><el-input v-model="form.password_confirm" size="large" type="password" show-password autocomplete="new-password" /></el-form-item>
        </div>
        <el-button class="submit-button" type="primary" size="large" native-type="submit" :loading="auth.busy">创建账户</el-button>
      </el-form>
      <p class="switch-copy">已经有账户？<RouterLink :to="{ name: 'login', query: route.query }">返回登录</RouterLink></p>
    </div>
  </section>
</template>

<style scoped>
.register-page { max-width: 880px; padding-top: 70px; padding-bottom: 50px; }
.register-card { padding: clamp(28px, 6vw, 58px); }
header { margin-bottom: 36px; }
header h1 { margin: 10px 0 12px; font: 500 clamp(36px, 5vw, 56px)/1 var(--font-display); letter-spacing: -.035em; }
header > p:last-child { color: var(--muted); }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; column-gap: 24px; }
.submit-button { width: 100%; margin-top: 8px; }
.switch-copy { margin: 24px 0 0; text-align: center; color: var(--muted); font-size: 13px; }
.switch-copy a { color: var(--accent-dark); font-weight: 600; }
@media (max-width: 650px) { .form-grid { grid-template-columns: 1fr; } .desktop-spacer { display: none; } .register-page { padding-top: 40px; } }
</style>
