<template>
  <img :src="logo" alt="FGITO" class="object-contain" />
</template>

<script setup>
// Central brand logo. To change the logo everywhere, replace the single file
// crm/public/images/logo.png (served at /assets/crm/images/logo.png).
// Use :src (runtime binding) so Vite treats it as a backend URL, not a bundled asset.
//
// Prefer the stored brand_logo: crm/setup/branding.py stamps it with ?v=<mtime>, so
// replacing logo.png busts the 12h /assets cache. Fall back to the plain path for the
// first paint, before FCRM Settings has loaded.
import { computed } from 'vue'
import { getSettings } from '@/stores/settings'

const { brand } = getSettings()
const logo = computed(() => brand.logo || '/assets/crm/images/logo.png')
</script>
