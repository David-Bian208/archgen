// 文本安全输出过滤器 - V3.8 HTML 实体解码增强版
export function escapeText(text) {
  if (text == null) return ''
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
    .replace(/%/g, '％') // 全角百分号
    .replace(/≥/g, '≥') // HTML 实体
    .replace(/！/g, '!') // 中文感叹号转英文
    .replace(/，/g, ',') // 中文逗号转英文
    .replace(/（/g, '(') // 中文括号
    .replace(/）/g, ')') // 中文括号
    .replace(/【/g, '[') // 中文方括号
    .replace(/】/g, ']') // 中文方括号
    .replace(/"/g, '"') // 中文引号
    .replace(/"/g, '"') // 中文引号
}

// V3.8 新增：HTML 实体解码函数（前端双保险）
export function decodeHTMLEntities(text) {
  if (text == null) return ''
  const entities = {
    '&amp;': '&',
    '&lt;': '<',
    '&gt;': '>',
    '&quot;': '"',
    '&#39;': "'",
    '&apos;': "'",
    '&nbsp;': ' ',
    '&ge;': '≥',
    '&le;': '≤',
  }
  let result = String(text)
  for (const [entity, char] of Object.entries(entities)) {
    result = result.replace(new RegExp(entity, 'g'), char)
  }
  return result
}
