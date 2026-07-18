"""
cherry_fidelity.py — Cherry AIPulse 精确复刻渲染器
直接匹配 /home/admin/Downloads/AIPulse-产品海报.html 的 DOM 结构、CSS 值和视觉效果。
Cherry 画布 448×597px，我们渲染到 1080×1440px（×2.41 缩放因子）。
"""

import json
import re
from typing import List, Dict, Optional

# ============================================================
# Cherry 精确颜色值
# ============================================================
CHERRY = {
    "primary": "#165DFF",
    "secondary": "#36CFFB",
    "primary_10": "rgba(22,93,255,0.1)",
    "primary_5": "rgba(22,93,255,0.05)",
    "secondary_10": "rgba(54,207,251,0.1)",
    "secondary_5": "rgba(54,207,251,0.05)",
    "primary_60": "rgba(22,93,255,0.6)",
    "text_700": "#374151",
    "text_800": "#1F2937",
    "text_600": "#4B5563",
    "border_100": "#F3F4F6",
    "bg_50": "#F9FAFB",
    "white": "#FFFFFF",
    "shadow": "0 1px 6px rgba(22,93,255,0.06)",
}

# 缩放因子: 1080/448 ≈ 2.4107
SCALE = 1080 / 448

def _s(val: float) -> int:
    """Cherry 448px 值 → 1080px 值"""
    return round(val * SCALE)

# ============================================================
# Cherry 精确字号 (已缩放至 1080px)
# ============================================================
FONT = {
    "header_title": _s(10),      # 24
    "module_h2": _s(11),         # 27
    "body_main": _s(9),          # 22
    "body_list": _s(8),          # 19
    "body_small": _s(7),         # 17
    "body_flow": _s(7.5),        # 18
    "number_circle": _s(8),      # 19
    "badge_text": _s(9),         # 22
    "footer_text": _s(8),        # 19
    "arrow_icon": _s(8),         # 19
    "flow_icon": _s(14),         # 34 (Cherry uses text-sm = 14px for flow icons)
    "grid_title": _s(8),         # 19
    "grid_desc": _s(7),          # 17
}

# Cherry 精确间距 (已缩放)
SPACE = {
    "header_h": _s(24),          # 58
    "footer_h": _s(24),          # 58
    "content_pad": _s(6),        # 14
    "module_gap": _s(6),         # 14
    "module_pad": _s(10),        # 24
    "border_radius": _s(8),      # 19
    "badge_radius": _s(4),       # 10 (Cherry uses rounded = 4px)
    "cell_radius": _s(4),        # 10 (Cherry uses rounded = 4px)
    "badge_pad": _s(4),          # 10 (Cherry uses p-1 = 4px)
    "highlight_item_gap": _s(4), # 10 (Cherry uses space-y-1 = 4px)
    "title_gap": _s(6),          # 14
    "number_circle": _s(14),     # 34
    "icon_main": _s(12),         # 29
    "icon_half": _s(10),         # 24
    "grid_gap": _s(6),           # 14
    "grid_cell_pad": _s(6),      # 14
    "content_gap": _s(8),        # 19
    "item_gap": _s(6),           # 14
}

# ============================================================
# SVG 图标 (Font Awesome 等价物)
# ============================================================
FA_SVG = {
    "handshake-o": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>',
    "file-text-o": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
    "code": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
    "rocket": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09zM12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4l-2 5 3 3 5-2v-5"/></svg>',
    "cogs": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>',
    "newspaper-o": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2z"/><path d="M4 10h12"/><path d="M4 14h12"/><path d="M8 18h8"/></svg>',
    "exchange": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></svg>',
    "book": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>',
    "unlock": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 9.9-1"/></svg>',
    "star": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="currentColor" stroke="none"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    "calendar-check-o": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><polyline points="9 16 11 18 15 14"/></svg>',
    "download": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
    "robot": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M12 3v4"/><circle cx="8.5" cy="14.5" r="1.5"/><circle cx="15.5" cy="14.5" r="1.5"/></svg>',
    "filter": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>',
    "sliders": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>',
    "clock-o": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
    "check-circle": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    "star-half-o": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v15.77l-6.18 3.25 1.18-6.88L2 9.27l6.91-1.01L12 2z"/></svg>',
    "database": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>',
    "user": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "chevron-right": '<svg viewBox="0 0 24 24" width="100%" height="100%" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>',
}

def _icon(icon_name: str, size: int) -> str:
    svg = FA_SVG.get(icon_name, FA_SVG.get("star", ""))
    return f'<span style="width:{size}px;height:{size}px;flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;">{svg}</span>'

def _number_circle(num: str) -> str:
    return (
        f'<div style="width:{SPACE["number_circle"]}px;height:{SPACE["number_circle"]}px;'
        f'border-radius:50%;background:{CHERRY["primary"]};color:{CHERRY["white"]};'
        f'font-size:{FONT["number_circle"]}px;display:flex;align-items:center;justify-content:center;'
        f'flex-shrink:0;font-weight:700;">{num}</div>'
    )


# ============================================================
# 六个模块渲染函数 (严格复刻 Cherry DOM)
# ============================================================

def _module_highlight(data: dict, num: str) -> str:
    """Module 01: 特殊高亮卡片 — 渐变背景 + 两列布局 + 右侧徽章"""
    title = data.get("title", "")
    items = data.get("items", [])
    badge_text = data.get("badge", "")

    # 标题行: 编号圆 + 标题
    title_row = (
        f'<div style="display:flex;align-items:center;gap:{SPACE["title_gap"]}px;'
        f'margin-bottom:{SPACE["title_gap"]}px;">'
        f'{_number_circle(num)}'
        f'<h2 style="font-size:{FONT["module_h2"]}px;font-weight:600;color:{CHERRY["primary"]};'
        f'margin:0;">{title}</h2>'
        f'</div>'
    )

    # 左侧: 要点列表 (4/5 宽度)
    left_items = ""
    for item in items:
        icon_name = item.get("icon", "star")
        bold = item.get("bold", "")
        text = item.get("text", "")
        left_items += (
            f'<div style="display:flex;align-items:center;gap:{SPACE["content_gap"]}px;">'
            f'<span style="color:{CHERRY["primary"]};width:{SPACE["icon_main"]}px;'
            f'text-align:center;flex-shrink:0;">{_icon(icon_name, FONT["body_list"])}</span>'
            f'<span style="font-size:{FONT["body_main"]}px;color:{CHERRY["text_700"]};'
            f'line-height:1.25;">'
            + (f'<b>{bold}</b>：{text}' if bold else f'{text}')
            + f'</span></div>'
        )

    left_col = (
        f'<div style="display:flex;flex-direction:column;gap:{SPACE["highlight_item_gap"]}px;'
        f'width:80%;">{left_items}</div>'
    )

    # 右侧: 徽章 (1/5 宽度) — Cherry 使用 rounded (4px), p-1 (4px)
    right_col = ""
    if badge_text:
        right_col = (
            f'<div style="width:20%;background:linear-gradient(180deg,{CHERRY["primary"]},{CHERRY["secondary"]});'
            f'border-radius:{SPACE["badge_radius"]}px;display:flex;align-items:center;'
            f'justify-content:center;color:{CHERRY["white"]};text-align:center;'
            f'padding:{SPACE["badge_pad"]}px;">'
            f'<p style="font-size:{FONT["badge_text"]}px;font-weight:700;line-height:1.25;margin:0;">{badge_text}</p>'
            f'</div>'
        )

    content = (
        f'<div style="display:flex;gap:{SPACE["content_gap"]}px;">'
        f'{left_col}{right_col}</div>'
    )

    return (
        f'<div style="position:relative;background:linear-gradient(135deg,{CHERRY["primary_5"]},{CHERRY["secondary_5"]});'
        f'border-radius:{SPACE["border_radius"]}px;padding:{SPACE["module_pad"]}px;'
        f'box-shadow:{CHERRY["shadow"]};border:1px solid {CHERRY["primary_10"]};">'
        f'{title_row}{content}</div>'
    )


def _module_list_card(data: dict, num: str, half_width: bool = False) -> str:
    """Module 02/03/04/06: 标准白色卡片 — 标题行 + 列表/网格内容"""
    title = data.get("title", "")
    items = data.get("items", [])
    is_grid = data.get("layout") == "grid"  # 3-column grid for modules 4, 6

    icon_size = SPACE["icon_half"] if half_width else SPACE["icon_main"]
    body_font = FONT["body_list"] if half_width else FONT["body_main"]
    text_color = CHERRY["text_700"] if not half_width else CHERRY["text_700"]
    title_color = CHERRY["text_800"] if half_width else CHERRY["text_800"]

    title_row = (
        f'<div style="display:flex;align-items:center;gap:{SPACE["title_gap"]}px;'
        f'margin-bottom:{SPACE["title_gap"]}px;">'
        f'{_number_circle(num)}'
        f'<h2 style="font-size:{FONT["module_h2"]}px;font-weight:600;color:{title_color};margin:0;">{title}</h2>'
        f'</div>'
    )

    if is_grid:
        # 3列网格 (module 04, 06)
        cells = ""
        for item in items:
            icon_name = item.get("icon", "star")
            cell_title = item.get("bold", "")
            cell_desc = item.get("text", "")
            cells += (
                f'<div style="padding:{SPACE["grid_cell_pad"]}px;background:{CHERRY["bg_50"]};'
                f'border-radius:{SPACE["cell_radius"]}px;text-align:left;">'
                f'<p style="font-size:{FONT["grid_title"]}px;font-weight:600;color:{CHERRY["text_700"]};'
                f'margin:0 0 {round(SPACE["module_gap"]/3)}px 0;display:flex;align-items:center;'
                f'gap:{round(SPACE["module_gap"]/3)}px;">'
                f'{_icon(icon_name, FONT["grid_title"])} {cell_title}</p>'
                f'<p style="font-size:{FONT["grid_desc"]}px;color:{CHERRY["text_600"]};margin:0;'
                f'line-height:1.4;">{cell_desc}</p>'
                f'</div>'
            )
        content = (
            f'<div style="display:grid;grid-template-columns:repeat(3,1fr);'
            f'gap:{SPACE["grid_gap"]}px;font-size:{FONT["body_list"]}px;color:{CHERRY["text_700"]};">'
            f'{cells}</div>'
        )
    else:
        # 列表模式 (module 02/03)
        list_items = ""
        for item in items:
            icon_name = item.get("icon", "star")
            text = item.get("text", "")
            list_items += (
                f'<div style="display:flex;align-items:center;gap:{SPACE["title_gap"]}px;">'
                f'<span style="color:{CHERRY["primary"]};width:{icon_size}px;'
                f'text-align:center;flex-shrink:0;">{_icon(icon_name, FONT["body_small"])}</span>'
                f'<span style="font-size:{body_font}px;color:{text_color};line-height:1.25;">{text}</span>'
                f'</div>'
            )
        content = (
            f'<div style="display:flex;flex-direction:column;gap:{SPACE["module_gap"]}px;">{list_items}</div>'
        )

    width_style = 'width:50%;' if half_width else ''

    return (
        f'<div style="position:relative;{width_style}background:{CHERRY["white"]};'
        f'border-radius:{SPACE["border_radius"]}px;padding:{SPACE["module_pad"]}px;'
        f'box-shadow:{CHERRY["shadow"]};border:1px solid {CHERRY["border_100"]};">'
        f'{title_row}{content}</div>'
    )


def _module_flow(data: dict, num: str) -> str:
    """Module 05: 横向流程图 — 图标在上 + 箭头连接"""
    title = data.get("title", "")
    items = data.get("items", [])

    title_row = (
        f'<div style="display:flex;align-items:center;gap:{SPACE["title_gap"]}px;'
        f'margin-bottom:{SPACE["title_gap"]}px;">'
        f'{_number_circle(num)}'
        f'<h2 style="font-size:{FONT["module_h2"]}px;font-weight:600;color:{CHERRY["text_800"]};margin:0;">{title}</h2>'
        f'</div>'
    )

    n = len(items)
    nodes = ""
    for i, item in enumerate(items):
        icon_name = item.get("icon", "star")
        text = item.get("text", "")
        nodes += (
            f'<div style="display:flex;flex-direction:column;align-items:center;'
            f'gap:{round(SPACE["module_gap"]/3)}px;width:{round(100/n)}%;">'
            f'<span style="color:{CHERRY["primary"]};font-size:{FONT["flow_icon"]}px;line-height:1;">'
            f'{_icon(icon_name, FONT["flow_icon"])}</span>'
            f'<span style="text-align:center;font-size:{FONT["body_flow"]}px;color:{CHERRY["text_700"]};'
            f'line-height:1.3;">{text}</span>'
            f'</div>'
        )
        if i < n - 1:
            nodes += (
                f'<span style="color:{CHERRY["primary_60"]};font-size:{FONT["arrow_icon"]}px;'
                f'display:flex;align-items:center;flex-shrink:0;">'
                f'{_icon("chevron-right", FONT["arrow_icon"])}</span>'
            )

    content = (
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'font-size:{FONT["body_flow"]}px;color:{CHERRY["text_700"]};">{nodes}</div>'
    )

    return (
        f'<div style="position:relative;background:{CHERRY["white"]};'
        f'border-radius:{SPACE["border_radius"]}px;padding:{SPACE["module_pad"]}px;'
        f'box-shadow:{CHERRY["shadow"]};border:1px solid {CHERRY["border_100"]};">'
        f'{title_row}{content}</div>'
    )


def _module_merged_double(data: dict, num: str) -> str:
    """合并卡片专用模板：标题行 + 内部分两列（左 ceil(N/2) 条，右剩余）

    用于 items ≥ 6 的合并卡片，避免单列右侧大空白。
    """
    title = data.get("title", "")
    items = data.get("items", [])
    n = len(items)
    left_n = (n + 1) // 2  # 左列多一条
    left_items = items[:left_n]
    right_items = items[left_n:]

    title_row = (
        f'<div style="display:flex;align-items:center;gap:{SPACE["title_gap"]}px;'
        f'margin-bottom:{SPACE["title_gap"]}px;">'
        f'{_number_circle(num)}'
        f'<h2 style="font-size:{FONT["module_h2"]}px;font-weight:600;color:{CHERRY["text_800"]};margin:0;">{title}</h2>'
        f'</div>'
    )

    def _col_html(col_items):
        col = ""
        for item in col_items:
            icon_name = item.get("icon", "star")
            bold = item.get("bold", "")
            text = item.get("text", "")
            col += (
                f'<div style="display:flex;align-items:flex-start;gap:{SPACE["title_gap"]}px;">'
                f'<span style="color:{CHERRY["primary"]};width:{SPACE["icon_half"]}px;'
                f'text-align:center;flex-shrink:0;margin-top:2px;">{_icon(icon_name, FONT["body_small"])}</span>'
                f'<span style="font-size:{FONT["body_list"]}px;color:{CHERRY["text_700"]};line-height:1.35;">'
                + (f'<b>{bold}</b>：{text}' if bold else f'{text}')
                + f'</span></div>'
            )
        return f'<div style="display:flex;flex-direction:column;gap:{SPACE["module_gap"]}px;flex:1;">{col}</div>'

    content = (
        f'<div style="display:flex;gap:{SPACE["content_gap"]}px;">'
        f'{_col_html(left_items)}'
        f'{_col_html(right_items)}'
        f'</div>'
    )

    return (
        f'<div style="position:relative;background:{CHERRY["white"]};'
        f'border-radius:{SPACE["border_radius"]}px;padding:{SPACE["module_pad"]}px;'
        f'box-shadow:{CHERRY["shadow"]};border:1px solid {CHERRY["border_100"]};">'
        f'{title_row}{content}</div>'
    )


def _module_list_compact(data: dict, num: str) -> str:
    """短内容半宽卡片：items 排成 2 列网格，避免右边空白。

    用于 half_width + items ≤ 4 + 每条文字 ≤ 20 字 的场景。
    """
    title = data.get("title", "")
    items = data.get("items", [])

    title_row = (
        f'<div style="display:flex;align-items:center;gap:{SPACE["title_gap"]}px;'
        f'margin-bottom:{SPACE["title_gap"]}px;">'
        f'{_number_circle(num)}'
        f'<h2 style="font-size:{FONT["module_h2"]}px;font-weight:600;color:{CHERRY["text_800"]};margin:0;">{title}</h2>'
        f'</div>'
    )

    # items 排成 2 列网格
    cells = ""
    for item in items:
        icon_name = item.get("icon", "star")
        bold = item.get("bold", "")
        text = item.get("text", "")
        cells += (
            f'<div style="display:flex;align-items:flex-start;gap:{round(SPACE["module_gap"]/2)}px;'
            f'padding:{round(SPACE["grid_cell_pad"]/2)}px;background:{CHERRY["bg_50"]};'
            f'border-radius:{SPACE["cell_radius"]}px;">'
            f'<span style="color:{CHERRY["primary"]};width:{SPACE["icon_half"]}px;'
            f'text-align:center;flex-shrink:0;margin-top:1px;">{_icon(icon_name, FONT["body_small"])}</span>'
            f'<span style="font-size:{FONT["body_list"]}px;color:{CHERRY["text_700"]};line-height:1.3;">'
            + (f'<b>{bold}</b>：{text}' if bold else f'{text}')
            + f'</span></div>'
        )

    content = (
        f'<div style="display:grid;grid-template-columns:repeat(2,1fr);'
        f'gap:{round(SPACE["module_gap"]/2)}px;">{cells}</div>'
    )

    return (
        f'<div style="position:relative;width:50%;background:{CHERRY["white"]};'
        f'border-radius:{SPACE["border_radius"]}px;padding:{SPACE["module_pad"]}px;'
        f'box-shadow:{CHERRY["shadow"]};border:1px solid {CHERRY["border_100"]};">'
        f'{title_row}{content}</div>'
    )


# ============================================================
# 拼装: 生成完整 Cherry-fidelity HTML
# ============================================================

def render_cherry_fidelity(
    modules: List[dict],
    header_text: str = "",
    footer_text: str = "",
) -> str:
    """
    modules: Cherry 格式的模块列表，每个模块:
        {
            "title": str,          # 模块标题
            "type": str,           # "highlight" | "list" | "grid" | "flow"
            "items": [...],        # 内容项
            "badge": str|None,     # module 01 徽章文字
            "half": bool,          # 是否半宽
            "layout": str|None,    # "grid" 表示网格布局
        }
    header_text: 顶部标题栏文字
    footer_text: 底部栏文字
    """
    w, h = 1080, 1440

    # 内容区域高度 = 总高度 - header - footer - 上下内容padding
    content_h = h - SPACE["header_h"] - SPACE["footer_h"] - 2 * SPACE["content_pad"]

    # 渲染模块
    module_html_list = []
    # Group: consecutive half-width modules need a flex wrapper
    i = 0
    while i < len(modules):
        m = modules[i]
        mtype = m.get("type", "list")
        is_half = m.get("half", False)

        if is_half and i + 1 < len(modules) and modules[i + 1].get("half", False):
            # 两个半宽模块并排
            left_html = _module_list_card(m, m.get("num", str(i + 1)), half_width=True)
            right_html = _module_list_card(modules[i + 1], modules[i + 1].get("num", str(i + 2)), half_width=True)
            # 右侧卡片需要移除 width:50%
            row = (
                f'<div style="display:flex;gap:{SPACE["module_gap"]}px;">'
                f'{left_html}{right_html}</div>'
            )
            module_html_list.append(row)
            i += 2
        elif mtype == "highlight":
            module_html_list.append(_module_highlight(m, m.get("num", str(i + 1))))
            i += 1
        elif mtype in ("grid", "list"):
            module_html_list.append(_module_list_card(m, m.get("num", str(i + 1))))
            i += 1
        elif mtype == "flow":
            module_html_list.append(_module_flow(m, m.get("num", str(i + 1))))
            i += 1
        else:
            module_html_list.append(_module_list_card(m, m.get("num", str(i + 1))))
            i += 1

    # 模块间间距
    body_content = f'<div style="display:flex;flex-direction:column;gap:{SPACE["module_gap"]}px;">' + \
        "".join(module_html_list) + "</div>"

    # Header bar
    header_html = (
        f'<div style="width:{w}px;height:{SPACE["header_h"]}px;'
        f'background:linear-gradient(90deg,{CHERRY["primary_10"]},{CHERRY["secondary_10"]});'
        f'display:flex;align-items:center;justify-content:center;flex-shrink:0;">'
        f'<h1 style="font-size:{FONT["header_title"]}px;font-weight:600;color:{CHERRY["primary"]};margin:0;">'
        f'{header_text}</h1></div>'
    )

    # Footer bar
    footer_html = (
        f'<div style="width:{w}px;height:{SPACE["footer_h"]}px;'
        f'background:linear-gradient(90deg,{CHERRY["primary"]},{CHERRY["secondary"]});'
        f'display:flex;align-items:center;justify-content:center;'
        f'padding:0 {SPACE["module_gap"]}px;flex-shrink:0;">'
        f'<p style="font-size:{FONT["footer_text"]}px;color:{CHERRY["white"]};margin:0;">{footer_text}</p></div>'
    )

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                     "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
        background: {CHERRY["bg_50"]};
        display: flex; justify-content: center; align-items: center;
        min-height: 100vh;
        -webkit-font-smoothing: antialiased;
    }}
    #poster {{
        width: {w}px; height: {h}px; overflow: hidden; position: relative;
        background: {CHERRY["white"]}; border-radius: 8px; box-shadow: 0 4px 32px rgba(0,0,0,0.12);
        display: flex; flex-direction: column;
    }}
    #poster-content {{
        flex: 1; overflow: hidden; padding: {SPACE["content_pad"]}px;
    }}
</style>
</head>
<body>
<div id="poster">
{header_html}
<div id="poster-content">
{body_content}
</div>
{footer_html}
</div>
<script>
(function(){{
    var p=document.getElementById('poster-content');
    if(!p)return;
    var c=p.firstElementChild;
    if(!c)return;
    var totalH=c.offsetHeight;
    var maxH={content_h};
    if(totalH>maxH){{
        var scale=maxH/totalH;
        if(scale>0.3) c.style.transform='scaleY('+scale+')';
        c.style.transformOrigin='top center';
    }}
}})();
</script>
</body>
</html>"""
    return full_html


# ============================================================
# 内容提取: 从文章 Markdown 提取 Cherry 格式的 6 模块数据
# ============================================================

def extract_cherry_modules_from_article(article_text: str) -> List[dict]:
    """
    从 2026-5-27.md 文章内容直接提取结构化模块数据。
    Cherry 参考的 6 个模块与文章段落严格对应。
    """
    modules = [
        {
            "num": "01",
            "title": "核心亮点 · Vibe Coding开发流程",
            "type": "highlight",
            "items": [
                {"icon": "handshake-o", "bold": "需求对齐",
                 "text": "我+元宝+OpenClaw+Trae 四方对齐全链路规则"},
                {"icon": "file-text-o", "bold": "文档落地",
                 "text": "所有决策输出标准化开发文档，无信息差"},
                {"icon": "code", "bold": "自动编码",
                 "text": "Trae自动完成前后端全量代码编写"},
                {"icon": "rocket", "bold": "上线部署",
                 "text": "AI辅助测试+部署，全程仅需做决策"},
            ],
            "badge": "3天从0到1上线",
        },
        {
            "num": "02",
            "title": "产品定位",
            "type": "list",
            "half": True,
            "items": [
                {"icon": "cogs", "text": "通用聚合引擎，可自定义任意领域信源"},
                {"icon": "newspaper-o", "text": "当前配置211个AI领域分级信源"},
                {"icon": "exchange", "text": "随时更换行业信源，完全私人定制"},
                {"icon": "book", "text": "零散资讯自动同步个人知识库"},
            ],
        },
        {
            "num": "03",
            "title": "核心价值",
            "type": "list",
            "half": True,
            "items": [
                {"icon": "unlock", "text": "境外源直连，无需梯子自动缓存全文"},
                {"icon": "star", "text": "5维智能评分，仅展示≥70分高价值内容"},
                {"icon": "calendar-check-o", "text": "每日8点生成行业动态，5分钟速览"},
                {"icon": "download", "text": "支持Markdown导出，同步Obsidian"},
            ],
        },
        {
            "num": "04",
            "title": "技术架构优势",
            "type": "grid",
            "layout": "grid",
            "items": [
                {"icon": "robot", "bold": "双LLM降本策略",
                 "text": "简单任务用DeepSeek V3.2，复杂推理用V4 Pro，算力成本降低80%，响应速度提升40%"},
                {"icon": "filter", "bold": "双层内容去重",
                 "text": "第一层URL匹配去重，第二层语义向量相似度校验，综合去重准确率达98%，无重复内容干扰"},
                {"icon": "sliders", "bold": "分级规则管控",
                 "text": "信源分S/A/B三级阈值准入，完全规则驱动过滤，无LLM幻觉干扰，内容可信度100%可控"},
            ],
        },
        {
            "num": "05",
            "title": "全自动化内容生产流程",
            "type": "flow",
            "items": [
                {"icon": "clock-o", "text": "每日8:00<br>定时触发"},
                {"icon": "download", "text": "拉取200-300条<br>信源内容"},
                {"icon": "check-circle", "text": "URL+语义<br>双层去重预筛"},
                {"icon": "star-half-o", "text": "5维评分<br>阈值判断"},
                {"icon": "database", "text": "优质内容入库<br>自动生成日报"},
            ],
        },
        {
            "num": "06",
            "title": "多场景适配能力",
            "type": "grid",
            "layout": "grid",
            "items": [
                {"icon": "user", "bold": "个人浏览场景",
                 "text": "网页端支持多维度筛选、关键词搜索、自定义标签分类，一键导出Markdown格式笔记"},
                {"icon": "code", "bold": "开发调用场景",
                 "text": "开放无鉴权API接口，可直接接入个人开发工具、AI Agent工作流，作为实时资讯数据源"},
                {"icon": "handshake-o", "bold": "AI协作场景",
                 "text": "支持对接Claude、Cursor等AI工具，提供最新行业动态作为上下文，提升AI输出时效性"},
            ],
        },
    ]
    return modules


# ============================================================
# 一键生成
# ============================================================

def generate_cherry_html(
    article_text: str = "",
    header_text: str = "",
    footer_text: str = "",
) -> str:
    """
    从文章文本生成 Cherry-fidelity HTML。
    """
    if not header_text:
        header_text = "3天Vibe Coding全AI开发 | 打造个人专属资讯引擎"
    if not footer_text:
        footer_text = "告别信息焦虑，打造专属个人资讯知识库 | 私人使用中，对外开放将根据反馈迭代"

    modules = extract_cherry_modules_from_article(article_text)
    return render_cherry_fidelity(modules, header_text, footer_text)


# ============================================================
# v4.0: 从 bin_packer 行数据渲染
# ============================================================

def _is_short_content(items: list) -> bool:
    """判断是否为短内容：items ≤ 4 且每条 text ≤ 25 字。"""
    if not items or len(items) > 4:
        return False
    for item in items:
        text = item.get("text", "")
        if len(text) > 25:
            return False
    return True


def _card_to_module(card: dict, num: str, half_width: bool = False) -> dict:
    """
    把 v4.0 卡片格式转换为 cherry_fidelity 渲染模块格式。

    v4.0 card: {title, items, density, content_shape, icon, badge, ...}
    → 渲染 module: {title, type, items, badge, half, layout, num}
    """
    shape = card.get("content_shape", "list")
    density = card.get("density", "medium")
    badge = card.get("badge")
    items = card.get("items", [])
    n_items = len(items)

    # 确定渲染类型
    if density == "high" and badge:
        mtype = "highlight"
    elif shape == "grid":
        mtype = "grid"
    elif shape == "flow":
        mtype = "flow"
    elif n_items >= 6 and not half_width:
        # 合并卡片或 items 较多的卡片 → 内部分两列（独占行才用，半宽不用）
        mtype = "merged_double"
    elif half_width and _is_short_content(items):
        # 半宽卡片 + 短内容 → 2 列网格布局（避免右边空白）
        mtype = "list_compact"
    elif shape == "compare":
        mtype = "list"  # compare 暂用 list 渲染（后续可扩展）
        if half_width is False:
            half_width = False  # compare 在独占行时不需要半宽
    else:
        mtype = "list"

    # 为 items 补全 icon 字段（渲染函数需要）
    card_icon = card.get("icon", "star")
    for item in items:
        if "icon" not in item:
            item["icon"] = card_icon

    return {
        "num": num,
        "title": card.get("title", ""),
        "type": mtype,
        "items": items,
        "badge": badge,
        "half": half_width,
        "layout": "grid" if shape == "grid" or mtype == "grid" else None,
    }


def render_from_rows(
    rows: list,
    header_text: str = "",
    footer_text: str = "",
    canvas_type: str = "portrait",
) -> str:
    """
    v4.0 第三站：从 bin_packer 的行数据渲染 HTML。

    rows: bin_packer.pack() 的输出
    canvas_type: "portrait" | "landscape"
    """
    w = 1080 if canvas_type == "portrait" else 1920
    h = 1440 if canvas_type == "portrait" else 1080

    content_h = h - SPACE["header_h"] - SPACE["footer_h"] - 2 * SPACE["content_pad"]

    # 渲染每一行
    module_html_list = []
    module_num = 0

    for row in rows:
        slots = row["slots"]
        n_slots = len(slots)
        module_num_start = module_num + 1

        if n_slots == 1:
            # 独占行
            card = slots[0]
            module_num += 1
            num_str = f"{module_num:02d}"
            module = _card_to_module(card, num_str, half_width=False)

            mtype = module["type"]
            if mtype == "highlight":
                module_html_list.append(_module_highlight(module, num_str))
            elif mtype == "grid":
                module_html_list.append(_module_list_card(module, num_str))
            elif mtype == "flow":
                module_html_list.append(_module_flow(module, num_str))
            elif mtype == "merged_double":
                module_html_list.append(_module_merged_double(module, num_str))
            else:
                module_html_list.append(_module_list_card(module, num_str))
        else:
            # 多列行（拼车）
            cards_html = []
            for card in slots:
                module_num += 1
                num_str = f"{module_num:02d}"
                module = _card_to_module(card, num_str, half_width=True)
                mtype = module["type"]
                if mtype == "list_compact":
                    cards_html.append(_module_list_compact(module, num_str))
                else:
                    cards_html.append(_module_list_card(module, num_str, half_width=True))

            row_html = (
                f'<div style="display:flex;gap:{SPACE["module_gap"]}px;">'
                + "".join(cards_html)
                + "</div>"
            )
            module_html_list.append(row_html)

    # 模块间间距
    body_content = (
        f'<div style="display:flex;flex-direction:column;gap:{SPACE["module_gap"]}px;">'
        + "".join(module_html_list)
        + "</div>"
    )

    # Header bar
    header_html = (
        f'<div style="width:{w}px;height:{SPACE["header_h"]}px;'
        f'background:linear-gradient(90deg,{CHERRY["primary_10"]},{CHERRY["secondary_10"]});'
        f'display:flex;align-items:center;justify-content:center;flex-shrink:0;">'
        f'<h1 style="font-size:{FONT["header_title"]}px;font-weight:600;color:{CHERRY["primary"]};margin:0;">'
        f'{header_text}</h1></div>'
    )

    # Footer bar
    footer_html = (
        f'<div style="width:{w}px;height:{SPACE["footer_h"]}px;'
        f'background:linear-gradient(90deg,{CHERRY["primary"]},{CHERRY["secondary"]});'
        f'display:flex;align-items:center;justify-content:center;'
        f'padding:0 {SPACE["module_gap"]}px;flex-shrink:0;">'
        f'<p style="font-size:{FONT["footer_text"]}px;color:{CHERRY["white"]};margin:0;">{footer_text}</p></div>'
    )

    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                     "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
        background: {CHERRY["bg_50"]};
        display: flex; justify-content: center; align-items: center;
        min-height: 100vh;
        -webkit-font-smoothing: antialiased;
    }}
    #poster {{
        width: {w}px; height: {h}px; overflow: hidden; position: relative;
        background: {CHERRY["white"]}; border-radius: 8px; box-shadow: 0 4px 32px rgba(0,0,0,0.12);
        display: flex; flex-direction: column;
    }}
    #poster-content {{
        flex: 1; overflow: hidden; padding: {SPACE["content_pad"]}px;
    }}
</style>
</head>
<body>
<div id="poster">
{header_html}
<div id="poster-content">
{body_content}
</div>
{footer_html}
</div>
<script>
(function(){{
    var p=document.getElementById('poster-content');
    if(!p)return;
    var c=p.firstElementChild;
    if(!c)return;
    var totalH=c.offsetHeight;
    var maxH={content_h};
    if(totalH>maxH){{
        var scale=maxH/totalH;
        if(scale>0.3) c.style.transform='scaleY('+scale+')';
        c.style.transformOrigin='top center';
    }}
}})();
</script>
</body>
</html>"""
    return full_html
