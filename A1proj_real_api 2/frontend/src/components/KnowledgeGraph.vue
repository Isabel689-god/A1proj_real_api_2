<template>
  <iframe
    src="/kg"
    class="kg-iframe"
    frameborder="0"
  />
</template>

<script setup lang="ts">
// 知识图谱直接嵌入后端 /kg 页面，保证前端与独立页面显示完全一致
</script>

<style scoped>
.kg-iframe {
  width: 100%;
  height: 100%;
  border: none;
  border-radius: 12px;
}
</style>
