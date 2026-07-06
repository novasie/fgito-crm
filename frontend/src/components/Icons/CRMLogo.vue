<template>
  <img :src="logo" alt="FGITO" class="object-contain" />
</template>

<script setup>
// Central brand logo. To change the logo everywhere, replace the single file
// crm/public/images/logo.png (served at /assets/crm/images/logo.png).
// Use :src (runtime binding) so Vite treats it as a backend URL, not a bundled asset.
const logo = '/assets/crm/images/logo.png'
</script>
