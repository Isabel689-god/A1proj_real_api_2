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

          <!-- 工具调用流程 -->
          <div v-if="msg.tool_calls && msg.tool_calls.length > 0" class="tool-flow">
            <div class="tool-flow-title">🔧 工作流程</div>
            <div
              v-for="(tc, i) in msg.tool_calls"
              :key="i"
              class="tool-card"
            >
              <div class="tool-card-head" @click="tc._open = !tc._open">
                <span class="tool-step-badge">{{ i + 1 }}</span>
                <span class="tool-card-label">{{ tc.label || tc.name }}</span>
                <span class="tool-card-arrow">{{ tc._open ? '▼' : '▶' }}</span>
              </div>
              <div v-if="tc._open" class="tool-card-body">
                <pre class="tool-output">{{ tc.output }}</pre>
              </div>
            </div>
          </div>

          <!-- token 用量 -->
          <div v-if="msg.token_usage" class="token-bar">
            📊 Token: 输入 {{ msg.token_usage.prompt }} + 输出 {{ msg.token_usage.completion }} = {{ msg.token_usage.total }}
          </div>

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

          <!-- 推荐下一步选项 -->
          <div v-if="msg.suggestions && msg.suggestions.length > 0" class="suggestions-bar">
            <div class="suggestions-label">💡 推荐下一步</div>
            <div class="suggestions-chips">
              <button
                v-for="(s, i) in msg.suggestions"
                :key="i"
                class="suggestion-chip"
                @click="$emit('suggestion-click', s)"
              >
                {{ i + 1 }}. {{ s }}
              </button>
            </div>
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

defineEmits<{
  'suggestion-click': [text: string]
}>();

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
  background: var(--primary-color);
  color: var(--text-inverse); display: flex; align-items: center; justify-content: center;
}

.ai-sparkle-avatar svg {
  width: 16px;
  height: 16px;
}

.user-txt-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--bg-card);
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
  background: var(--bg-soft);
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
  background: var(--bg-soft) !important;
  color: var(--accent-cyan) !important;
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 13px;
}

:deep(.gemini-markdown pre) {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  padding: 12px 16px;
  overflow-x: auto;
  margin: 10px 0;
}
:deep(.gemini-markdown pre code) {
  background: none !important;
  padding: 0;
  color: var(--text-primary) !important;
}

:deep(.gemini-markdown table) {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0;
  font-size: 13px;
}
:deep(.gemini-markdown th) {
  background: var(--bg-hover);
  color: var(--primary-light);
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  border-bottom: 2px solid var(--primary-color);
}
:deep(.gemini-markdown td) {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-glass);
  color: var(--text-primary);
}
:deep(.gemini-markdown tr:hover td) {
  background: var(--bg-hover);
}

:deep(.gemini-markdown h2) {
  color: var(--primary-light) !important;
  font-size: 17px;
  font-weight: 700;
  margin: 18px 0 10px 0;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border-glass);
}

:deep(.gemini-markdown h3),
:deep(.gemini-markdown .cn-heading) {
  color: var(--primary-light) !important;
  font-size: 16px;
  font-weight: 700;
  margin: 16px 0 8px 0;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border-glass);
}

:deep(.gemini-markdown ul),
:deep(.gemini-markdown ol) {
  padding-left: 20px;
  margin: 8px 0;
}
:deep(.gemini-markdown li) {
  margin-bottom: 4px;
  color: var(--text-primary);
}

:deep(.gemini-markdown blockquote) {
  border-left: 3px solid var(--primary-color);
  padding: 8px 14px;
  margin: 10px 0;
  background: var(--bg-hover);
  color: var(--text-secondary);
  border-radius: 0 6px 6px 0;
}

:deep(.gemini-markdown hr) {
  border: none;
  border-top: 1px solid var(--border-glass);
  margin: 14px 0;
}

:deep(.gemini-markdown a) {
  color: var(--primary-light);
  text-decoration: underline;
}

/* 工具调用流程 */
.tool-flow {
  margin: 12px 0;
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  border-radius: 10px;
  padding: 12px;
}
.tool-flow-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary-light);
  margin-bottom: 8px;
}
.tool-card {
  margin-bottom: 4px;
}
.tool-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}
.tool-card-head:hover {
  background: var(--bg-hover);
}
.tool-step-badge {
  width: 20px; height: 20px;
  background: var(--primary-color);
  color: var(--text-inverse);
  border-radius: 50%;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.tool-card-label {
  flex: 1;
  font-size: 13px;
  color: var(--text-primary);
}
.tool-card-arrow {
  font-size: 10px;
  color: var(--text-muted);
}
.tool-card-body {
  margin-top: 4px;
  padding: 8px 12px;
  background: var(--bg-soft);
  border-radius: 6px;
}
.tool-output {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
  margin: 0;
}

/* token 用量 */
.token-bar {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 8px;
  padding: 4px 0;
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
  background-color: var(--bg-soft) !important;
  border: 1px solid var(--border-glass) !important;
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
  background: var(--bg-card);
  padding: 12px; border-radius: 8px;
  border-left: 3px solid var(--primary-dark);
  line-height: 1.5;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.suggestions-bar {
  margin-top: 16px;
  padding: 12px;
  background: var(--bg-glass);
  border: 1px solid var(--border-glass);
  border-radius: 10px;
}
.suggestions-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 8px;
}
.suggestions-chips {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.suggestion-chip {
  display: block;
  width: 100%;
  text-align: left;
  padding: 10px 14px;
  background: var(--bg-hover);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.suggestion-chip:hover {
  background: var(--bg-hover);
  border-color: var(--primary-color);
  color: var(--primary-color);
}
</style>

<style>
/* v-html 全局样式 — scoped 无法穿透 innerHTML */
.gemini-markdown h2 {
  color: #00c8b4 !important;
  font-size: 18px !important;
  font-weight: 700 !important;
  margin: 20px 0 10px 0 !important;
  padding-bottom: 6px !important;
  border-bottom: 1px solid rgba(0,200,180,0.3) !important;
}
.gemini-markdown h3 {
  color: #00c8b4 !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  margin: 16px 0 8px 0 !important;
  padding-bottom: 6px !important;
  border-bottom: 1px solid rgba(0,200,180,0.3) !important;
}
</style>
