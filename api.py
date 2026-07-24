"""排布 (PaiBu) API 路由"""
import json
import os
import time
import asyncio
import logging
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, Body

logger = logging.getLogger("paibu.api")
router = APIRouter(prefix="/api", tags=["paibu"])

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _is_real_llm() -> bool:
    return os.environ.get("USE_REAL_LLM", "true").lower() == "true"


# ============================================================
# POST /api/extract — 拆卡片
# 响应格式: {success, cards, header, footer, llm}
# ============================================================
@router.post("/extract")
async def extract_cards(request: Dict = Body(...)):
    try:
        content = request.get("content", "").strip()
        detail_level = request.get("detail_level", "medium")

        if not content:
            return {"success": False, "error": "内容为空"}

        use_real = _is_real_llm()
        llm_label = "real"

        if use_real:
            try:
                from llm_client import extract_cards_from_article
                extracted = extract_cards_from_article(content, detail_level=detail_level)
            except Exception:
                import traceback
                traceback.print_exc()
                from test_pipeline import mock_llm_extract
                extracted = mock_llm_extract(content, detail_level=detail_level)
                llm_label = "mock(LLM故障自动回退)"
        else:
            from test_pipeline import mock_llm_extract
            extracted = mock_llm_extract(content, detail_level=detail_level)
            llm_label = "mock"

        cards = extracted["cards"]

        if not use_real:
            if detail_level == "compact":
                for c in cards:
                    for it in c.get("items", []):
                        text = it.get("text", "")
                        if text and len(text) > 15:
                            it["text"] = text[:15] + "..."
                llm_label += " +compact(mock)"
            elif detail_level == "detailed":
                suffixes = [
                    "，提升整体效率与用户体验", "，加速业务迭代与交付",
                    "，降低运维成本与风险", "，增强系统稳定性与可靠性",
                    "，优化资源配置与利用率", "，实现全链路自动化管理",
                ]
                for c in cards:
                    for j, it in enumerate(c.get("items", [])):
                        text = it.get("text", "")
                        if text and len(text) > 5:
                            it["text"] = text + suffixes[j % len(suffixes)]
                llm_label += " +detailed(mock)"

        return {
            "success": True,
            "cards": cards,
            "header": extracted.get("header_title", ""),
            "footer": extracted.get("footer_text", ""),
            "llm": llm_label,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


# ============================================================
# POST /api/generate — 生成海报 HTML
# 响应格式: {success, url}
# ============================================================
@router.post("/generate")
async def generate_poster(request: Dict = Body(...)):
    try:
        cards = request.get("cards", [])
        canvas_type = request.get("canvas", "portrait")
        header = request.get("header", "")
        footer = request.get("footer", "")
        theme = request.get("theme", "blue")
        auto_height = request.get("auto_height", False)

        if not cards:
            return {"success": False, "error": "卡片为空"}

        import bin_packer
        import cherry_fidelity as cf

        rows = bin_packer.pack(cards, canvas_type)
        html = cf.render_from_rows(rows, header, footer, canvas_type, theme=theme)

        if auto_height:
            html = html.replace("<body>", '<body><script>window.forceAutoHeight=true;</script>')

        fname = f"poster_{int(time.time() * 1000)}_{canvas_type}.html"
        (OUTPUT_DIR / fname).write_text(html, encoding="utf-8")

        return {"success": True, "url": fname}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


# ============================================================
# POST /api/screenshot — 海报截图
# 响应格式: {success, url}
# ============================================================
@router.post("/screenshot")
async def screenshot_poster(request: Dict = Body(...)):
    try:
        file_name = request.get("file", "")
        canvas_type = request.get("canvas", "portrait")
        auto_height = request.get("auto_height", False)

        real_file = file_name.split("?")[0]
        html_path = OUTPUT_DIR / real_file
        if not html_path.exists():
            return {"success": False, "error": f"文件不存在: {file_name}"}

        html_content = html_path.read_text(encoding="utf-8")
        if auto_height:
            html_content = html_content.replace("<body>", '<body><script>window.forceAutoHeight=true;</script>')

        png_path = OUTPUT_DIR / real_file.replace(".html", ".png")
        size_map = {"portrait": "xiaohongshu", "landscape": "ppt", "square": "default"}
        size = size_map.get(canvas_type, "default")

        from screenshot import ScreenshotService
        svc = ScreenshotService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(svc.capture(html_content, str(png_path), size))
        loop.close()

        if png_path.exists():
            return {"success": True, "url": png_path.name}
        return {"success": False, "error": "截图失败"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


# ============================================================
# POST /api/enrich — 单卡片详略调整
# 响应格式: {success, card}
# ============================================================
@router.post("/enrich")
async def enrich_single_card(request: Dict = Body(...)):
    try:
        card = request.get("card", {})
        level = request.get("level", "detailed")

        if not card:
            return {"success": False, "error": "卡片为空"}

        if level == "medium":
            return {"success": True, "card": card}

        use_real = _is_real_llm()
        if use_real:
            try:
                if level == "compact":
                    from llm_client import compact_card_items
                    result = compact_card_items(card)
                else:
                    from llm_client import enrich_card_items
                    result = enrich_card_items(card)
                return {"success": True, "card": result}
            except Exception:
                import traceback
                traceback.print_exc()

        items = card.get("items", [])
        if level == "compact":
            for it in items:
                text = it.get("text", "")
                if text and len(text) > 15:
                    it["text"] = text[:15] + "..."
        else:
            suffixes = [
                "，提升整体效率与用户体验", "，加速业务迭代与交付",
                "，降低运维成本与风险", "，增强系统稳定性与可靠性",
            ]
            for j, it in enumerate(items):
                text = it.get("text", "")
                if text and len(text) > 5:
                    it["text"] = text + suffixes[j % len(suffixes)]
        card["items"] = items
        return {"success": True, "card": card}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


# ============================================================
# POST /api/enrich_all — 批量详略调整
# 响应格式: {success, cards}
# ============================================================
@router.post("/enrich_all")
async def enrich_all_cards(request: Dict = Body(...)):
    try:
        cards = request.get("cards", [])
        level = request.get("level", "medium")

        if not cards:
            return {"success": False, "error": "卡片列表为空"}

        if level == "medium":
            return {"success": True, "cards": cards}

        use_real = _is_real_llm()
        for i, card in enumerate(cards):
            if use_real:
                try:
                    if level == "compact":
                        from llm_client import compact_card_items
                        cards[i] = compact_card_items(card)
                    else:
                        from llm_client import enrich_card_items
                        cards[i] = enrich_card_items(card)
                except Exception:
                    import traceback
                    traceback.print_exc()
                else:
                    continue

            items = card.get("items", [])
            if level == "compact":
                for it in items:
                    text = it.get("text", "")
                    if text and len(text) > 15:
                        it["text"] = text[:15] + "..."
            else:
                suffixes = [
                    "，提升整体效率与用户体验", "，加速业务迭代与交付",
                    "，降低运维成本与风险", "，增强系统稳定性与可靠性",
                    "，优化资源配置与利用率", "，实现全链路自动化管理",
                ]
                for j, it in enumerate(items):
                    text = it.get("text", "")
                    if text and len(text) > 5:
                        it["text"] = text + suffixes[j % len(suffixes)]
            cards[i] = card

        return {"success": True, "cards": cards}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}
