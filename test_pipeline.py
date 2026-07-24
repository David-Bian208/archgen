#!/usr/bin/env python3
"""
海报生成测试脚本 —— 跑 v4 完整流程
用法: python test_pipeline.py <文章内容或文件路径>
"""
import json
import sys
import pathlib
from datetime import datetime

import bin_packer
import cherry_fidelity


def _fallback_extract(article_text: str, header_title: str, max_len: int = 20) -> list:
    """
    兜底处理：没有 ## 章节标题时，智能拆分文本为卡片。
    支持：纯文本段落、# 一级标题、数字编号、换行分隔。
    """
    import re
    
    lines = article_text.strip().split('\n')
    cards = []
    
    # 策略1：尝试按 # 一级标题拆分
    sections = _split_by_level1_headers(lines)
    if len(sections) > 1:
        for i, (title, body_lines) in enumerate(sections):
            items = _lines_to_items(body_lines, max_len)
            if items:
                cards.append({
                    'id': i + 1,
                    'title': title,
                    'items': items,
                    'density': 'medium',
                    'content_shape': 'list',
                    'semantic_weight': 'secondary',
                    'icon': 'star',
                    'badge': None,
                })
        if cards:
            return cards
    
    # 策略2：按空行拆分为多个卡片（每段一个卡片，段内句子为 items）
    paragraphs = re.split(r'\n\s*\n', article_text.strip())
    if len(paragraphs) >= 2:
        for i, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                continue
            para_lines = para.split('\n')
            # 去掉 # 标题行
            if para_lines[0].startswith('#'):
                title = para_lines[0].lstrip('#').strip()
                body = para_lines[1:]
            else:
                title = para_lines[0][:30] + ('...' if len(para_lines[0]) > 30 else '')
                body = para_lines
            
            items = _lines_to_items(body, max_len)
            if not items:
                # 如果没拆出 items，用整个段落作为一条 text
                text = ' '.join(l.strip() for l in para_lines if l.strip())
                if text:
                    items = [{'bold': None, 'text': text[:max_len*5]}]
            
            if items:
                cards.append({
                    'id': len(cards) + 1,
                    'title': title,
                    'items': items[:8],  # 最多 8 条
                    'density': 'medium',
                    'content_shape': 'list',
                    'semantic_weight': 'secondary',
                    'icon': 'star',
                    'badge': None,
                })
        if cards:
            return cards
    
    # 策略3：全文本作为一个卡片，每句话一行
    clean = article_text.strip()
    if clean:
        lines = [l.strip() for l in clean.split('\n') if l.strip()]
        # 去标题行
        if lines and lines[0].startswith('#'):
            lines = lines[1:]
        
        items = _lines_to_items(lines, max_len)
        if not items:
            # 拆短句
            sentences = re.split(r'[。！？\n]', clean)
            for s in sentences:
                s = s.strip()
                if s and len(s) > 2:
                    items.append({'bold': None, 'text': s[:max_len*4]})
        
        if items:
            cards.append({
                'id': 1,
                'title': header_title,
                'items': items[:8],
                'density': 'medium',
                'content_shape': 'list',
                'semantic_weight': 'primary',
                'icon': 'star',
                'badge': None,
            })
    
    return cards


def _split_by_level1_headers(lines: list) -> list:
    """按 # 一级标题拆分，返回 [(title, body_lines), ...]"""
    sections = []
    current_title = None
    current_body = []
    
    for line in lines:
        if line.startswith('# ') and not line.startswith('## '):
            if current_title is not None:
                sections.append((current_title, current_body))
            current_title = line.lstrip('#').strip()
            current_body = []
        else:
            current_body.append(line)
    
    if current_title is not None:
        sections.append((current_title, current_body))
    
    return sections


def _lines_to_items(lines: list, max_len: int = 20) -> list:
    """将文本行列表转为卡片 items"""
    items = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 去掉列表符号
        line = line.lstrip('- *•·1234567890.①②③④⑤⑥⑦⑧⑨⑩、）) ')
        line = line.strip()
        if not line:
            continue
        
        bold = None
        text = line
        if '：' in line:
            parts = line.split('：', 1)
            if len(parts[0]) <= 15:
                bold = parts[0].strip()
                text = parts[1].strip()
        
        items.append({'bold': bold, 'text': text[:max_len*3]})  # 宽松限制，大概字数
    return items


def mock_llm_extract(article_text: str, detail_level: str = "medium") -> dict:
    """
    模拟 LLM 拆卡片输出（用于快速测试）
    真实场景替换为调用 LLM API（用 stage1_extract_prompt_v4 的 SYSTEM_PROMPT）
    detail_level: compact/medium/detailed 控制每条要点长度
    """
    # 根据详略控制最大长度
    max_len_map = {"compact": 12, "medium": 20, "detailed": 40}
    max_text_len = max_len_map.get(detail_level, 20)
    
    # 简单按 ## 分块
    lines = article_text.strip().split('\n')
    header_title = lines[0].lstrip('#').strip() if lines else '未命名'
    
    cards = []
    current_card = None
    card_id = 1
    
    for line in lines[1:]:
        line = line.rstrip()
        if line.startswith('## '):
            if current_card:
                cards.append(current_card)
            title = line[3:].strip()
            current_card = {
                'id': card_id,
                'title': title,
                'items': [],
                'density': 'medium',
                'content_shape': 'list',
                'semantic_weight': 'secondary',
                'icon': 'star',
                'badge': None,
            }
            card_id += 1
        elif line.startswith('- ') and current_card:
            text = line[2:].strip()
            bold = None
            if '：' in text:
                parts = text.split('：', 1)
                if len(parts[0]) <= 12:
                    bold = parts[0].strip()
                    text = parts[1].strip()
            current_card['items'].append({
                'bold': bold,
                'text': text,
            })
    
    if current_card:
        cards.append(current_card)
    
    # ======== 兜底：没有 ## 章节时，智能拆分 ========
    if not cards:
        cards = _fallback_extract(article_text, header_title, max_text_len)
    
    # 第一张设为 primary + high density + badge（如果有量化）
    if cards:
        cards[0]['semantic_weight'] = 'primary'
        cards[0]['density'] = 'high'
        # 找有数字的亮点当 badge
        all_items_text = ' '.join(i.get('text', '') + (i.get('bold') or '') for c in cards for i in c.get('items', []))
        import re
        nums = re.findall(r'\d+%|\d+天|\d+个|\d+维|\d+层|\d+倍', all_items_text)
        if nums:
            cards[0]['badge'] = nums[0] + '亮眼表现'
    
    # flow 检测（含"流程/步骤/阶段/触发→拉取→"这类词）
    flow_keywords = ['流程', '步骤', '阶段', '触发', '→', '-']
    for card in cards:
        title = card.get('title', '')
        items_text = ' '.join(i.get('text', '') for i in card.get('items', []))
        if any(kw in title or kw in items_text for kw in flow_keywords):
            if len(card.get('items', [])) >= 3:
                card['content_shape'] = 'flow'
                card['icon'] = 'chevron-right'
    
    # compare 检测（含"对比/vs/比较/区别/差异"这类词）
    compare_keywords = ['对比', 'vs', 'VS', '比较', '区别', '差异', '优劣']
    for card in cards:
        title = card.get('title', '')
        if any(kw in title for kw in compare_keywords):
            card['content_shape'] = 'compare'
            card['icon'] = 'scale'
            # 确保至少 4 项才好看
            if len(card.get('items', [])) < 4:
                card['items'] = card.get('items', [])[:]  # 至少保留现有的
    
    return {
        'thinking': f'从 {len(cards)} 个章节拆出 {sum(len(c.get("items", [])) for c in cards)} 条要点',
        'header_title': header_title,
        'footer_text': 'AI 自动生成 · 告别信息焦虑',
        'cards': cards,
    }


def generate(article_text: str, output_prefix: str = 'test') -> dict:
    """跑完整流程"""
    
    # 1. LLM 拆卡片
    stage1_result = mock_llm_extract(article_text)
    cards = stage1_result['cards']
    header_title = stage1_result['header_title']
    footer_text = stage1_result['footer_text']
    
    print(f'📋 拆出 {len(cards)} 张卡片，共 {sum(len(c.get("items", [])) for c in cards)} 条要点')
    for c in cards:
        print(f'  #{c["id"]} {c["title"]} ({c["density"]}/{c["content_shape"]}/{c["semantic_weight"]})')
    
    warning = ''
    
    # 2. 装箱 + 渲染（竖版 + 横版）
    outputs = {}
    for canvas_type in ['portrait', 'landscape']:
        rows = bin_packer.pack(cards, canvas_type)
        n_rows = len(rows)
        max_rows = bin_packer.CANVAS[canvas_type]['max_rows']
        
        if n_rows > max_rows:
            warning += f' {canvas_type}超出行数限制({n_rows}/{max_rows})，已合并相邻卡片'
        
        html = cherry_fidelity.render_from_rows(
            rows=rows,
            header_text=header_title,
            footer_text=footer_text,
            canvas_type=canvas_type,
        )
        
        out_path = f'output/{output_prefix}_{canvas_type}.html'
        pathlib.Path(out_path).write_text(html, encoding='utf-8')
        outputs[canvas_type] = out_path
        print(f'✅ {canvas_type}: {out_path} ({n_rows}/{max_rows} 行)')
    
    return {
        'success': True,
        'portrait': outputs['portrait'],
        'landscape': outputs['landscape'],
        'warning': warning,
        'cards_count': len(cards),
    }


def main():
    if len(sys.argv) < 2:
        print('用法: python test_pipeline.py <文章内容或文件路径>')
        print('示例: python test_pipeline.py my_article.md')
        sys.exit(1)
    
    arg = sys.argv[1]
    
    # 是文件路径就读文件，否则是内容
    if pathlib.Path(arg).exists():
        content = pathlib.Path(arg).read_text(encoding='utf-8')
    else:
        content = arg
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result = generate(content, output_prefix=f'test_{timestamp}')
    
    print('\n' + '='*60)
    print(f'竖版预览: http://localhost:8080/{result["portrait"]}')
    print(f'横版预览: http://localhost:8080/{result["landscape"]}')
    if result['warning']:
        print(f'⚠️  注意: {result["warning"]}')
    print('='*60)


if __name__ == '__main__':
    main()
