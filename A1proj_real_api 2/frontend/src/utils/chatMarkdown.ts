import MarkdownIt from 'markdown-it';

const MarkdownConstructor = (MarkdownIt as any).default || MarkdownIt;

const md = new MarkdownConstructor({
  html: false,
  linkify: true,
  typographer: false,
  breaks: true,
});

// 使用 CSS 变量适配主题，而非硬编码颜色
const H2_STYLE =
  'color:var(--primary-color);font-size:17px;font-weight:700;margin:20px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--border-light)';
const H3_STYLE =
  'color:var(--primary-light,#00b4a0);font-size:15px;font-weight:600;margin:14px 0 6px';
const BOLD_STYLE =
  'color:var(--text-primary);font-weight:600';
const LIST_STYLE =
  'margin:4px 0;padding-left:18px;line-height:1.7;color:var(--text-primary)';
const PARA_STYLE =
  'margin:6px 0;line-height:1.65;color:var(--text-primary)';

export function renderMarkdown(text: string): string {
  if (!text) return '';

  text = text.replace(/：\s*\n\s*/g, '：');
  // 确保 ## 标题前有两个换行，markdown-it 需要空行才能认作标题
  text = text.replace(/([^\n])(##\s)/g, '$1\n\n$2');
  text = text.replace(/^##\s/gm, '\n## ');  // 文首的 ## 也补空行

  try {
    let html = md.render(text);

    html = html.replace(/<h2>/g, `<h2 style="${H2_STYLE}">`);
    html = html.replace(/<h3>/g, `<h3 style="${H3_STYLE}">`);
    html = html.replace(/<strong>/g, `<strong style="${BOLD_STYLE}">`);
    html = html.replace(/<ul>/g, `<ul style="${LIST_STYLE}">`);
    html = html.replace(/<ol>/g, `<ol style="${LIST_STYLE}">`);
    html = html.replace(/<p>/g, `<p style="${PARA_STYLE}">`);

    return html;
  } catch (error) {
    console.error('Markdown 渲染失败:', error);
    return text.replace(/\n/g, '<br>');
  }
}
