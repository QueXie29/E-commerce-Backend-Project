<script setup lang="ts">
import { watch, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    src?: string
    alt: string
    compact?: boolean
  }>(),
  {
    src: '',
    compact: false,
  },
)

const failed = ref(false)

watch(
  () => props.src,
  () => {
    failed.value = false
  },
)
</script>

<template>
  <div class="product-image" :class="{ 'product-image--compact': compact }">
    <img v-if="src && !failed" :src="src" :alt="alt" loading="lazy" @error="failed = true" />
    <div v-else class="product-image__placeholder" role="img" :aria-label="`${alt}暂无图片`">
      <span>MINI</span>
      <small>暂无图片</small>
    </div>
  </div>
</template>

<style scoped>
.product-image {
  position: relative;
  width: 100%;
  overflow: hidden;
  aspect-ratio: 4 / 3;
  background: linear-gradient(145deg, #f3f6f4, #e8eee9);
}

.product-image--compact {
  width: 86px;
  min-width: 86px;
  aspect-ratio: 1;
  border-radius: 14px;
}

.product-image img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
  transition: transform 0.35s ease;
}

.product-image:hover img {
  transform: scale(1.025);
}

.product-image__placeholder {
  width: 100%;
  height: 100%;
  display: grid;
  place-content: center;
  gap: 4px;
  color: #68766b;
  text-align: center;
  letter-spacing: 0.14em;
}

.product-image__placeholder span {
  font-size: 18px;
  font-weight: 750;
}

.product-image__placeholder small {
  font-size: 11px;
  letter-spacing: 0.04em;
}
</style>
