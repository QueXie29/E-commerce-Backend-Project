<script setup lang="ts">
import { computed } from 'vue'

import type { OrderStatus } from '@/shared/api/contracts'

const props = defineProps<{
  status: OrderStatus
}>()

const statusMeta = computed(() => {
  const map: Record<OrderStatus, { label: string; type: 'warning' | 'success' | 'info' }> = {
    pending: { label: '待支付', type: 'warning' },
    paid: { label: '已支付', type: 'success' },
    cancelled: { label: '已取消', type: 'info' },
  }
  return map[props.status]
})
</script>

<template>
  <el-tag :type="statusMeta.type" effect="light" round>{{ statusMeta.label }}</el-tag>
</template>
