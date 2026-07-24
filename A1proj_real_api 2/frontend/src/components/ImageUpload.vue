<template>
  <div class="gemini-inline-uploader">
    <el-upload
      action="#"
      :auto-upload="false"
      :show-file-list="false"
      :on-change="handleImageChange"
      accept="image/*"
    >
      <button class="icon-trigger-btn" type="button" title="上传故障图片（多模态通道）">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          <circle cx="8.5" cy="8.5" r="1.5"></circle>
          <polyline points="21 15 16 10 5 21"></polyline>
        </svg>
      </button>
    </el-upload>
  </div>
</template>

<script setup lang="ts">
import { useChatStore } from '../stores/chat';
import { ElMessage } from 'element-plus';

const store = useChatStore();

const handleImageChange = (file: any) => {
  if (!file.raw) return;
  const isLt8M = file.raw.size / 1024 / 1024 < 8; // 保持你原有的8MB校验
  if (!isLt8M) {
    ElMessage.error('上传的故障图片大小不能超过 8MB!');
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    if (e.target?.result) {
      store.setUploadedImage(file.name, e.target.result as string);
    }
  };
  reader.readAsDataURL(file.raw);
};
</script>

<style scoped>
.gemini-inline-uploader {
  display: flex;
  align-items: center;
}
.icon-trigger-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  transition: background 0.2s;
}
.icon-trigger-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--primary-light);
}
.icon-trigger-btn svg {
  width: 18px;
  height: 18px;
}
</style>