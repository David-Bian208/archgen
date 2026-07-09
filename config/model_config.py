"""
DeepSeek V4 模型分配配置

用途：
    - 定义 V4-Pro 和 V4-Flash 的模型 ID
    - 按业务场景分配模型（call_name → model_id）
    - 提供统一入口：get_model_for_scene(call_name) → "deepseek-v4-pro" | "deepseek-v4-flash"

灰度开关：
    - 环境变量 ARCHGEN_FORCE_FLASH=true → 所有场景强制使用 Flash
    - 用于低成本测试全流程连通性

上线节奏：
    - Day 1-2：ARCHGEN_FORCE_FLASH=true，跑通全流程
    - Day 3：关闭开关，Pro 场景切回 V4-Pro
    - Day 4 (2026-07-24)：旧模型 deepseek-chat 下线，无感切换完成

参考：
    DeepSeek API 文档: https://api-docs.deepseek.com/zh-cn/updates/
"""

import os

# ========== V4 模型定义 ==========
V4_PRO = "deepseek-v4-pro"
V4_FLASH = "deepseek-v4-flash"

# ========== 灰度开关 ==========
_force_flash = os.environ.get("ARCHGEN_FORCE_FLASH", "").lower() in ("true", "1", "yes")


# ========== 场景 → 模型映射表（40 个场景）==========

SCENE_MODEL_MAP = {
    # ========================================
    # Pro 核心生成（13 个场景）
    # 直接面向用户的最终产出 + 核心决策链
    # ========================================

    # --- 提纲与结构（4 个）---
    "结构推荐": V4_PRO,              # generate_outline_v2 Step 1（框架推导）
    "结构推荐_final": V4_PRO,        # generate_outline_v2 Step 2（最终提纲，核心输出）
    "content_structure": V4_PRO,     # generate_content_structure（分段大纲）
    "outline_versions": V4_PRO,      # generate_outline_versions（多风格提纲）
    "slot_outline": V4_PRO,          # generate_slot_outline（单槽位提纲，血肉质量关键）

    # --- 全文与段落（9 个）---
    "full_article_stage1": V4_PRO,   # generate_full_article 阶段1：信息整合
    "full_article_stage2": V4_PRO,   # generate_full_article 阶段2：结构化扩展
    "full_article_stage3": V4_PRO,   # generate_full_article 阶段3：优化润色
    "generate_paragraph_draft": V4_PRO,  # generate_full_article 内层：逐段展开
    "polish_article": V4_PRO,        # generate_full_article 内层：拼接润色
    "summarize_material": V4_FLASH,  # generate_full_article 内层：素材摘要压缩
    "全文生成": V4_PRO,              # ai_generate_full_content（一键全文）
    "generate_section": V4_PRO,      # ai_generate_section（单段落生成）
    "rewrite_section": V4_PRO,       # ai_rewrite_section（用户指令重写）
    "智能补全": V4_PRO,              # smart_fill_content（逐段判断 + 补全）

    # --- 槽位系统核心（3 个）---
    "generate_slots": V4_PRO,        # generate_slots（核心创意规划）
    "slot_preview": V4_PRO,          # slot_content_preview（槽位内容预览）
    "ask_followup": V4_PRO,          # ask_followup（用户追问 AI 回复）

    # --- 选题决策核心（1 个）---
    "角度推荐 · 人设匹配": V4_PRO,   # recommend_angles Step 3（临门一脚，锐度关键）

    # ========================================
    # Flash 辅助分析（27 个场景）
    # 分类过滤 / 评分检测 / 简单生成 / 辅助补充
    # ========================================

    # --- 选题 & 方向（7 个）---
    "方向提名": V4_FLASH,            # _auto_recommend_topics Step 2
    "选题评分": V4_FLASH,            # _auto_recommend_topics Step 4
    "MCP题材推荐": V4_FLASH,         # mcp_topic_suggestion
    "方向分析": V4_FLASH,            # analyze_directions_v2
    "角度推荐 · 素材扫描": V4_FLASH, # recommend_angles Step 1
    "角度推荐 · 覆盖度评分": V4_FLASH, # recommend_angles Step 2

    # --- 检索 & 过滤（3 个）---
    "mcp_title_filter": V4_FLASH,    # llm_filter_by_titles（LLM 标题筛选）
    "mcp_search_summary": V4_FLASH,  # mcp_search（MCP 全文检索总结）
    "aipulse_match": V4_FLASH,       # _match_aipulse_by_llm（AI-Pulse 语义匹配）

    # --- 检测 & 审核（3 个）---
    "完整度评估": V4_FLASH,          # evaluate_completeness（门卫模式）
    "方向检测": V4_FLASH,            # check_direction（Gatekeeper 审核）
    "section_alignment": V4_FLASH,   # check_direction_alignment（段落方向检测）

    # --- 补充 & 修正（7 个）---
    "AI推断补充": V4_FLASH,          # ai_infer_supplement（Cherry 原则）
    "ai_supplement": V4_FLASH,       # ai_auto_supplement（方案 A，含 Web 降级）
    "supplement_3": V4_FLASH,        # 第三次补充信息
    "fix_direction": V4_FLASH,       # fix_direction_issue（方向问题修正）
    "generate_field": V4_FLASH,      # ai_generate_field（表单字段填充）
    "knowledge_assess": V4_FLASH,    # knowledge_assessor.assess（L0-L4 分类）
    "degradation_generate": V4_FLASH,# degradation_chain.generate（降级链生成）

    # --- 框架 & 匹配（4 个）---
    "框架匹配": V4_FLASH,            # match_frameworks_v2
    "配图生成": V4_FLASH,            # suggest_framework_from_slots（7 选 1）
    "recommend_structures": V4_FLASH,# recommend_structures（旧 httpx，匹配模板）
    "recommend_structures_v2": V4_FLASH, # 新旧共存

    # --- 身份 & 其他（5 个）---
    "parse_persona": V4_FLASH,       # parse_persona（身份定位解析）
    "parse_persona_sync": V4_FLASH,   # _parse_persona_sync（同步解析）
    "auto_parse_persona": V4_FLASH,  # auto_parse_persona（启动后自动解析）
    "槽位关联分析": V4_FLASH,        # slot_relations（关系分类）
    "precheck_materials": V4_FLASH,   # pre_check_materials（素材可行性预检）

    # --- 批量处理（1 个）---
    "批量填充": V4_FLASH,            # batch_fill_v4（批量匹配，Flash 够用）

    # --- 旧调用路径（2 个，已废弃但保留兼容）---
    "analyze_directions": V4_FLASH,  # analyze_directions（v1 混合模式）
    "evaluate_direction": V4_FLASH,  # evaluate_user_direction（用户方向评估）
}


def get_model_for_scene(call_name: str) -> str:
    """
    根据业务场景返回 V4 模型 ID。

    Args:
        call_name: 场景名称（中文或英文，与 SCENE_MODEL_MAP 的 key 匹配）

    Returns:
        "deepseek-v4-pro" 或 "deepseek-v4-flash"

    优先级：
        1. 环境变量 ARCHGEN_FORCE_FLASH=true → 全部返回 Flash
        2. SCENE_MODEL_MAP 匹配 → 返回对应模型
        3. 未匹配 → 兜底返回 Flash
    """
    if _force_flash:
        return V4_FLASH
    return SCENE_MODEL_MAP.get(call_name, V4_FLASH)


def get_default_max_tokens(call_name: str) -> int:
    """
    根据场景返回推荐的 max_tokens。

    Pro 场景给更大输出空间（384K 上限），Flash 保持短平快。
    """
    model = get_model_for_scene(call_name)
    if model == V4_PRO:
        return 8192   # Pro 支持长输出
    return 2048       # Flash 短平快
