import MarkdownIt from 'markdown-it';

const MarkdownConstructor = (MarkdownIt as any).default || MarkdownIt;

const md = new MarkdownConstructor({
  html: true,
  linkify: true,
  typographer: true,
});

export function renderMarkdown(text: string): string {
  if (!text) return '';
  try {
    let html = md.render(text);
    // v-html 内联样式 — 不受 scoped CSS 限制
    html = html.replace(
      /<h2>/g,
      '<h2 style="color:#00c8b4;font-size:18px;font-weight:700;margin:18px 0 8px;padding-bottom:6px;border-bottom:1px solid rgba(0,200,180,0.3)">'
    );
    html = html.replace(
      /<h3>/g,
      '<h3 style="color:#00c8b4;font-size:16px;font-weight:700;margin:16px 0 8px;padding-bottom:6px;border-bottom:1px solid rgba(0,200,180,0.3)">'
    );
    return html;
  } catch (error) {
    console.error('Markdown 渲染失败:', error);
    return text;
  }
}
