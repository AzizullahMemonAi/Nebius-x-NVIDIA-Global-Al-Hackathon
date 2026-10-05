/**
 * Minimal, XSS-safe Markdown renderer for chat + panel bodies.
 * Input is HTML-escaped before any markup is generated, so only the subset
 * below can produce tags.
 */
import { esc } from './dom.js';

function inline(text) {
  let out = text;

  // inline code first so its contents are not further transformed
  const codeSpans = [];
  out = out.replace(/`([^`\n]+)`/g, (_m, code) => {
    codeSpans.push(code);
    return `\u0000CODE${codeSpans.length - 1}\u0000`;
  });

  out = out.replace(/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>');
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/(^|[\s(])\*([^*\n]+)\*/g, '$1<em>$2</em>');
  out = out.replace(/(^|[\s(])_([^_\n]+)_/g, '$1<em>$2</em>');
  out = out.replace(/~~([^~]+)~~/g, '<del>$1</del>');

  // links: [label](https://...) only, http(s) + relative
  out = out.replace(/\[([^\]\n]+)\]\(((?:https?:\/\/|\/)[^)\s]+)\)/g,
    (_m, label, href) => `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${label}</a>`);

  out = out.replace(/\u0000CODE(\d+)\u0000/g, (_m, i) => `<code>${esc(codeSpans[Number(i)])}</code>`);
  return out;
}

function renderTable(rows) {
  const cells = rows
    .map((row) => row.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim()));
  if (cells.length < 2) return '';
  const head = cells[0];
  const body = cells.slice(2);
  return (
    '<table><thead><tr>' +
    head.map((c) => `<th>${inline(c)}</th>`).join('') +
    '</tr></thead><tbody>' +
    body.map((row) => '<tr>' + row.map((c) => `<td>${inline(c)}</td>`).join('') + '</tr>').join('') +
    '</tbody></table>'
  );
}

/**
 * @param {string} source
 * @returns {string} HTML
 */
export function renderMarkdown(source) {
  if (!source) return '';
  const text = String(source).replace(/\r\n/g, '\n');
  const blocks = text.split(/\n{2,}/);
  const out = [];

  for (const block of blocks) {
    const trimmed = block.trim();
    if (!trimmed) continue;

    // fenced code
    const fence = trimmed.match(/^```([\w+-]*)\n?([\s\S]*?)\n?```$/);
    if (fence) {
      out.push(`<pre><code data-lang="${esc(fence[1] || '')}">${esc(fence[2])}</code></pre>`);
      continue;
    }

    // table
    if (/\|/.test(trimmed) && /^\|?[\s:|-]+\|[\s:|-]*$/.test(trimmed.split('\n')[1] || '')) {
      const table = renderTable(trimmed.split('\n'));
      if (table) { out.push(table); continue; }
    }

    const heading = trimmed.match(/^(#{1,4})\s+(.*)$/);
    if (heading) {
      const level = heading[1].length;
      out.push(`<h${level}>${inline(heading[2])}</h${level}>`);
      continue;
    }

    if (/^(-{3,}|\*{3,})$/.test(trimmed)) { out.push('<hr>'); continue; }

    if (/^>\s?/.test(trimmed)) {
      const text2 = trimmed.replace(/^>\s?/gm, '');
      out.push(`<blockquote>${renderMarkdown(text2)}</blockquote>`);
      continue;
    }

    const bullets = trimmed.match(/^[-*+]\s+([\s\S]+)$/);
    if (bullets) {
      const items = bullets[1].split('\n').filter((l) => /^\s*[-*+]\s+/.test(l))
        .map((l) => `<li>${inline(l.replace(/^\s*[-*+]\s+/, ''))}</li>`).join('');
      if (items) { out.push(`<ul>${items}</ul>`); continue; }
    }

    const ordered = trimmed.match(/^\d+[.)]\s+([\s\S]+)$/);
    if (ordered) {
      const items = ordered[1].split('\n').filter((l) => /^\s*\d+[.)]\s+/.test(l))
        .map((l) => `<li>${inline(l.replace(/^\s*\d+[.)]\s+/, ''))}</li>`).join('');
      if (items) { out.push(`<ol>${items}</ol>`); continue; }
    }

    out.push(`<p>${inline(trimmed).replace(/\n/g, '<br>')}</p>`);
  }

  return out.join('');
}

/** Render then colourise +/- diff lines inside a <pre>. */
export function renderDiff(patch) {
  const lines = esc(patch ?? '').split('\n');
  return lines
    .map((line) => {
      const cls = line.startsWith('+++') || line.startsWith('---') || line.startsWith('diff ') || line.startsWith('index ')
        ? 'diff-hunk'
        : line.startsWith('@@') ? 'diff-hunk'
          : line.startsWith('+') ? 'diff-add'
            : line.startsWith('-') ? 'diff-del'
              : '';
      return `<span class="diff-line ${cls}">${line || ' '}</span>`;
    })
    .join('\n');
}

export { esc };