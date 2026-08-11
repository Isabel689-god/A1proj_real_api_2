<template>
  <div class="composer-wrapper">
    <div class="gemini-capsule-box">

      <div v-if="store.uploadedImage" class="inline-preview-bar">
        <div class="preview-token">
          <img :src="store.uploadedImage.url" class="mini-thumb" />
          <span class="thumb-name">{{ store.uploadedImage.fileName || '已载入图像' }}</span>
          <button class="clear-thumb-btn" @click="store.clearUploadedImage">
            <el-icon><Close /></el-icon>
          </button>
        </div>
      </div>

      <textarea
        v-model="textInput"
        placeholder="请输入遇到的工业故障现象描述，或上传照片组合推理... (Ctrl + Enter 提报)"
        @keydown.ctrl.enter="handleSend"
        :disabled="store.loading"
        rows="1"
        class="capsule-textarea"
        ref="textareaRef"
        @input="adjustHeight"
      ></textarea>

      <div class="capsule-toolbar">
        <div class="toolbar-left-group">
          <div class="embedded-uploader-trigger">
            <ImageUpload />
          </div>
        </div>

        <div class="toolbar-right-group">
          <div class="calc-status" v-if="store.loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span style="font-size: 11px; margin-left: 6px; font-family: 'Cascadia Code', 'JetBrains Mono', ui-monospace, Consolas, monospace;">多模态链路计算中...</span>
          </div>

          <button
            class="circle-send-btn"
            :class="{ 'has-content': textInput.trim() || store.uploadedImage }"
            :disabled="store.loading || (!textInput.trim() && !store.uploadedImage)"
            @click="handleSend"
            title="提报发送"
          >
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <div class="bottom-disclaimer">AI 检索推理可能产生误差，请务必参照右侧 SOP 规程核对检修步骤。</div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue';
import { useChatStore } from '../stores/chat';
import { Loading, Close } from '@element-plus/icons-vue';
import ImageUpload from './ImageUpload.vue';
import { ElMessage } from 'element-plus';

const store = useChatStore();
const textInput = ref('');
const textareaRef = ref<HTMLTextAreaElement | null>(null);

// 让文本框像 Gemini 一样根据输入内容自动撑开高度
const adjustHeight = () => {
  const el = textareaRef.value;
  if (!el) return;
  el.style.height = 'auto'; // 先重置
  el.style.height = (el.scrollHeight > 160 ? 160 : el.scrollHeight) + 'px'; // 最大限制160px
};

const handleSend = async () => {
  if (store.loading) return;

  if (!textInput.value.trim() && !store.uploadedImage) {
    ElMessage.warning('请输入故障描述或上传设备照片！');
    return;
  }

  const rawText = textInput.value;
  textInput.value = '';

  await store.sendMessage(rawText);

  // 发送后重置输入框高度
  nextTick(() => {
    if (textareaRef.value) textareaRef.value.style.height = 'auto';
  });
};
</script>

<style scoped>
.composer-wrapper {
  padding: 10px 24px 20px;
  background: transparent;
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}

/* Gemini 核心胶囊框体设计 */
.gemini-capsule-box {
  width: 100%; max-width: 820px;
  background: var(--bg-card);
  border: 1px solid var(--border-glass);
  border-radius: 28px;
  padding: 14px 18px 10px;
  display: flex; flex-direction: column;
  transition: border-color 0.3s, box-shadow 0.3s;
  box-shadow: var(--shadow-card);
}

.gemini-capsule-box:focus-within {
  border-color: var(--primary-color);
  box-shadow: var(--shadow-sm);
}

/* 内嵌多模态预览卡片 */
.inline-preview-bar {
  display: flex;
  padding-bottom: 12px;
}

.preview-token {
  display: flex;
  align-items: center;
  background: var(--bg-soft);
  border: 1px solid var(--border-glass);
  padding: 4px 10px 4px 6px;
  border-radius: 12px;
  gap: 8px;
  box-shadow: var(--shadow-glass);
}

.mini-thumb {
  width: 32px;
  height: 32px;
  object-fit: cover;
  border-radius: 8px;
}

.thumb-name {
  font-size: 12px;
  color: var(--text-primary);
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.clear-thumb-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  padding: 2px;
  border-radius: 50%;
}

.clear-thumb-btn:hover {
  color: var(--danger);
  background: var(--bg-hover);
}

/* 隐形文本框 */
.capsule-textarea {
  width: 100%;
  height: 24px;
  min-height: 24px;
  background: transparent;
  border: none;
  outline: none;
  resize: none;
  color: var(--text-primary);
  font-size: 15px;
  line-height: 1.6;
  padding: 2px 4px;
  font-family: 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', system-ui, sans-serif;
}
.capsule-textarea::placeholder {
  color: var(--text-muted);
}

/* 底部轻量级控制条 */
.capsule-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-top: 10px;
}

.toolbar-left-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 适配胶囊风的轻量化下拉菜单 */
.gemini-mini-select :deep(.el-input__wrapper) {
  background-color: var(--bg-soft) !important;
  box-shadow: none !important;
  border: 1px solid var(--border-glass) !important;
  border-radius: 16px !important;
  padding: 1px 12px !important;
  height: 32px;
}
.gemini-mini-select :deep(.el-input__inner) {
  color: var(--text-secondary) !important;
  font-size: 12px;
}

.toolbar-right-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.calc-status {
  color: var(--primary-light);
  display: flex;
  align-items: center;
}

/* 发送圆形图标按钮 */
.circle-send-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: transparent;
  border: none;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: not-allowed;
  transition: all 0.2s ease;
}

.circle-send-btn.has-content {
  background: var(--primary-color);
  color: var(--text-inverse);
  cursor: pointer;
}
.circle-send-btn.has-content:hover {
  background: var(--primary-dark);
  transform: scale(1.05);
}

.circle-send-btn svg {
  width: 18px;
  height: 18px;
  transform: translateX(1px); /* 视觉微调中心点 */
}

/* 底部声明 */
.bottom-disclaimer {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 12px;
  text-align: center;
  letter-spacing: 0.5px;
}
</style>
