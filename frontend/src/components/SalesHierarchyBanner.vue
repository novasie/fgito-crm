<template>
  <div
    v-if="!isSidebarCollapsed && showBanner"
    class="flex flex-col gap-3 shadow-sm rounded-lg py-2.5 px-3 bg-surface-elevation-2 text-base"
  >
    <div class="flex items-start justify-between gap-2">
      <div class="inline-flex text-ink-gray-9 gap-2 items-center font-medium">
        <span class="lucide-info h-4" aria-hidden="true" />
        {{ __('Permissions update') }}
      </div>
      <button
        class="text-ink-gray-7 hover:text-ink-gray-8"
        :aria-label="__('Dismiss')"
        @click="dismiss"
      >
        <span class="lucide-x h-3.5" aria-hidden="true" />
      </button>
    </div>
    <div class="text-ink-gray-7 text-p-sm">
      {{ __('We are changing how permissions work in FGITO CRM') }}
    </div>
  </div>
</template>

<script setup>
import { useStorage } from '@vueuse/core'
import { computed } from 'vue'
import { usersStore } from '@/stores/users'

defineProps({
  isSidebarCollapsed: {
    type: Boolean,
    default: false,
  },
})

const { isManager } = usersStore()
const dismissed = useStorage('salesHierarchyBannerDismissed', false)

const showBanner = computed(() => !dismissed.value && isManager())

function dismiss() {
  dismissed.value = true
}
</script>
