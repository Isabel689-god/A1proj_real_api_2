<template>
  <div class="message-list-container" ref="listRef">
    <div class="gemini-viewport">
      <div
        v-for="msg in store.messages"
        :key="msg.id"
        :class="['stream-msg-row', msg.role]"
      >
        <div class="identity-side">
          <div v-if="msg.role === 'assistant'" class="ai-sparkle-avatar">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2l2.4 4.9 5.4.8-3.9 3.8.9 5.4-4.8-2.5-4.8 2.5.9-5.4-3.9-3.8 5.4-.8z" />
            </svg>
          </div>
          <div v-else class="user-txt-avatar">员</div>
        </div>

        <div class="main-content-flow">
          <div v-if="msg.role === 'user' && (msg.deviceModel || msg.imageUrl)" class="meta-inline-tag">
            <span v-if="msg.deviceModel" class="rag-chip">📟 靶向绑定: {{ msg.deviceModel }}</span>
            <div v-if="msg.imageUrl" class="img-bubble">
              <el-image :src="msg.imageUrl" :preview-src-list="[msg.imageUrl]" class="embedded-img" />
            </div>
          </div>

          <div v-html="renderMarkdown(msg.content)" class="gemini-markdown"></div>

          <div v-if="msg.sources && msg.sources.length > 0" class="gemini-sources-zone">
            <el-collapse class="flat-collapse">
              <el-collapse-item
                v-for="(src, index) in msg.sources"
                :key="index"
                :title="`🔍 [溯源-0${index + 1}] 《${src.source}》 - ${src.title}`"
              >
                <div class="flat-source-content">{{ src.content }}</div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { useChatStore } from '../stores/chat';
import { renderMarkdown } from '../utils/chatMarkdown';

const store = useChatStore();
const listRef = ref<HTMLElement | null>(null);

watch(() => store.messages.length, () => {
  nextTick(() => {
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight;
    }
  });
}, { deep: true });
</script>

<style scoped>
.message-list-container {
  flex: 1;
  padding: 40px 20px;
  overflow-y: auto;
  background: var(--bg-darker); /* 移除大面积蓝白色网格，统一过渡到优雅纯粹的工业深邃色 */
}

.gemini-viewport {
  max-width: 820px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 36px; /* 增大段落间隔，营造大厂模型的空间感与高级呼吸感 */
}

.stream-msg-row {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  animation: fadeIn 0.3s ease-out;
}

.stream-msg-row.user {
  flex-direction: row-reverse; /* 用户靠右排布，AI 靠左排布 */
}

/* 头像微缩设计 */
.identity-side {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
}

.ai-sparkle-avatar {
  width: 32px; height: 32px; border-radius: 50%;
  /* 柔和蓝紫渐变 */
  background: linear-gradient(135deg, #5c558c, #4a6596);
  color: white; display: flex; align-items: center; justify-content: center;
  box-shadow: 0 0 10px rgba(92, 85, 140, 0.3);
}

.ai-sparkle-avatar svg {
  width: 16px;
  height: 16px;
}

.user-txt-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #374151;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}

/* 主干展示流 */
.main-content-flow {
  flex: 1;
  max-width: calc(100% - 48px);
}

.stream-msg-row.user .main-content-flow {
  display: flex;
  flex-direction: column;
  align-items: flex-end; /* 用户提问文本行右对齐 */
}

/* 多模态图像元数据 */
.meta-inline-tag {
  margin-bottom: 8px;
}

.rag-chip {
  font-size: 11px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border-glass);
  padding: 3px 8px; border-radius: 12px;
  color: var(--accent-cyan);
}

.img-bubble {
  margin-top: 8px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border-glass);
  max-width: 240px;
}

.embedded-img {
  width: 100%;
  display: block;
}

/* Markdown 排版精细调优（完美融合底色） */
.gemini-markdown {
  color: var(--text-primary) !important;
  font-size: 15px;
  line-height: 1.62;
  word-break: break-word;
}

.stream-msg-row.user .gemini-markdown {
  background: var(--bg-glass); /* 通透玻璃质感 */
  border: 1px solid var(--border-glass);
  padding: 10px 16px; border-radius: 18px;
  max-width: 85%;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

:deep(.gemini-markdown p) {
  margin-bottom: 8px;
  color: var(--text-primary);
}

:deep(.gemini-markdown strong) {
  color: var(--primary-light) !important;
  font-weight: 600;
}

:deep(.gemini-markdown code) {
  background: rgba(255, 255, 255, 0.08) !important;
  color: var(--accent-cyan) !important;
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 13px;
}

/* 扁平化溯源组件 */
.gemini-sources-zone {
  margin-top: 14px;
  max-width: 100%;
}

.flat-collapse {
  border: none !important;
  background: transparent !important;
}

:deep(.flat-collapse .el-collapse-item__header) {
  background-color: rgba(255, 255, 255, 0.03) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  color: var(--text-secondary) !important;
  font-size: 12px !important;
  border-radius: 8px;
  padding: 0 12px;
  height: 36px;
  margin-bottom: 6px;
}

:deep(.flat-collapse .el-collapse-item__wrap) {
  background: transparent !important;
  border: none !important;
}

.flat-source-content {
  font-size: 13px; color: var(--text-secondary);
  background: rgba(0, 0, 0, 0.3);
  padding: 12px; border-radius: 8px;
  border-left: 3px solid var(--primary-dark);
  line-height: 1.5;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>