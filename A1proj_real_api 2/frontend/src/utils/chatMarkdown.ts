import MarkdownIt from 'markdown-it';

// 兼容性构造函数获取：防止 Vite 在处理 CommonJS 模块时丢失 default 属性
const MarkdownConstructor = (MarkdownIt as any).default || MarkdownIt;

const md = new MarkdownConstructor({
  html: true,        // 允许解析基础 HTML 标签
  linkify: true,     // 自动将文本中的 URL 链接转为可点击的超链接
  typographer: true, // 启用智能标点转换
});

/**
 * 核心导出函数：将大模型的 Markdown 文本转换为精美的网页 HTML
 * @param text 大模型传回的原始字符串
 */
export function renderMarkdown(text: string): string {
  if (!text) return '';
  try {
    return md.render(text);
  } catch (error) {
    console.error('Markdown 渲染失败:', error);
    return text; // 降级处理：渲染失败则返回原文本，确保不崩溃
  }
}