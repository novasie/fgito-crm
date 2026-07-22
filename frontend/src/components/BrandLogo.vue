<template>
  <div v-if="brand?.logo">
    <!-- object-contain (not cover) so the whole logo shows at its true aspect ratio -->
    <img :src="brand.logo" class="h-full w-full object-contain object-left" />
  </div>
  <CRMLogo v-else class="size-20 shrink-0 rounded" />
</template>

<script setup>
import CRMLogo from '@/components/Icons/CRMLogo.vue'

const brand = defineModel({ type: Object, default: () => ({}) })
</script>
