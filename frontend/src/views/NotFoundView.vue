<script setup lang="ts">
import { ArrowLeft } from '@lucide/vue'
</script>

<template>
  <main class="not-found page-shell">
    <p class="error-code">404</p>
    <p class="eyebrow">PAGE NOT FOUND</p>
    <h1>这件商品不在货架上</h1>
    <p>你访问的页面不存在，或者它已经换了位置。</p>
    <RouterLink class="primary-link" :to="{ name: 'product-list' }"><ArrowLeft :size="16" />回到商城</RouterLink>
  </main>
</template>

<style scoped>
.not-found { min-height: 70vh; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
.error-code { margin: 0; color: var(--accent); font: 500 clamp(100px, 21vw, 220px)/.75 var(--font-display); opacity: .16; }
h1 { margin: 16px 0 12px; font: 500 clamp(34px, 5vw, 58px) var(--font-display); }
.not-found > p:not(.error-code, .eyebrow) { margin: 0 0 28px; color: var(--muted); }
.primary-link { display: inline-flex; align-items: center; gap: 8px; }
</style>
