<!--
  En el celular solo se abren las pantallas pensadas para él (router › esCelular). Las
  demás llegan aquí: se avisa y se ofrecen las de celular que el usuario tiene.
-->
<template>
  <div class="bg-surface min-h-full flex items-center justify-center px-6" style="padding-top: env(safe-area-inset-top)">
    <div class="max-w-xs text-center">
      <div class="w-12 h-12 mx-auto rounded-2xl bg-white border border-surface-border flex items-center justify-center text-ink-light">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.6" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg>
      </div>
      <p class="text-[17px] font-semibold mt-4">Esta pantalla es para computadora</p>
      <p class="text-[13px] text-ink-muted mt-1.5">En el celular se ve mal; ábrela desde una computadora. Desde aquí puedes usar:</p>
      <EnlacesCelular class="justify-center mt-4" />
    </div>
  </div>
</template>

<script setup>
import EnlacesCelular from "@/components/EnlacesCelular.vue";
</script>
