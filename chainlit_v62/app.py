"""
行为观察助手 V6.4.3 - Chainlit 流式界面
实时展示 5 步临床推理过程，支持 ABC 引导式多轮对话

版本：V6.4.3
- V6.2: Chainlit UI + ABC 提取 + 输入验证
- V6.3: ABC 引导 + 语义判断
- V6.4: UI 优化 + 推理折叠
- V6.4.1: VAGUE_PATTERNS + 关键词分组 + LLM 超时
- V6.4.2: ABC 智能引导（B 回答含 C 信息自动识别）+ 中台数据记录
- V6.4.3: 完整对话记录 + 会话追踪（sessions 表）+ 错误日志
"""

import sys
import os
import json
import time
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import chainlit as cl

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.llm.openai_client import OpenAIClient
from app.agents.clinical_reasoning_engine import ClinicalReasoningEngine

# 初始化引擎
api_key = os.getenv("LLM_API_KEY", "sk-your-api-key-here")
base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
model = os.getenv("LLM_MODEL", "deepseek-chat")
llm_client = OpenAIClient(api_key=api_key, base_url=base_url, model=model)
engine = ClinicalReasoningEngine(llm_client)


# ===== 中台数据记录 =====
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'conversations.db')

def get_admin_db():
    """获取中台数据库连接"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            response_time_seconds REAL,
            scene_type TEXT,
            hypothesis TEXT
        )
    """)
    # V6.4.3 新增：完整对话记录表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE,
            status TEXT DEFAULT 'in_progress',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            error_message TEXT,
            total_turns INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn

def log_interaction(session_id, role, content, context="", scene_type=None, hypothesis=None, response_time=None):
    """记录所有对话交互到中台数据库（包括 ABC 引导中的对话）"""
    try:
        conn = get_admin_db()
        
        # 更新或创建 session 记录
        conn.execute("""
            INSERT OR IGNORE INTO sessions (session_id) VALUES (?)
        """, (session_id,))
        conn.commit()
        
        # 记录对话内容
        conn.execute(
            "INSERT INTO conversations (user_id, session_id, role, content, scene_type, hypothesis, response_time_seconds) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("anonymous", session_id, role, content, scene_type, hypothesis, response_time)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[AdminDB] 记录失败: {e}")

def log_conversation(session_id, role, content, scene_type=None, hypothesis=None, response_time=None):
    """记录对话到中台数据库（兼容旧接口）"""
    log_interaction(session_id, role, content, "", scene_type, hypothesis, response_time)


@cl.on_chat_start
async def on_chat_start():
    """V6.4 新增：开场白"""
    await cl.Message(
        content="""
# 🧠 行为观察助手

您好！我是专注于儿童行为支持的观察助手。

我们可以：
1. 对您观察到的行为进行分步剖析。
2. 探讨行为背后多种可能的原因。
3. 基于分析，提供可尝试的后续思路。

您可以从描述一次具体的行为事件开始，任何细节都有帮助。

> 📷 注：当前版本暂不支持图片上传，请用文字描述行为即可。
        """,
        author="系统"
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """V6.3 新增：处理用户消息"""
    user_input = message.content.strip()
    
    # 检查是否在 ABC 引导流程中
    abc_state = cl.user_session.get("abc_state")
    
    if abc_state and abc_state.get("in_progress"):
        await handle_abc_guidance(user_input, abc_state)
        return
    
    # 语义判断
    quality = engine.analyze_input_quality(user_input)
    q = quality.get("quality", "complete")
    
    if not quality.get("valid", True):
        if q == "vague":
            # 模糊输入 → 启动 ABC 教育
            await start_abc_education(user_input)
            return
        else:
            # 无效输入 → 直接拒绝
            await cl.Message(
                content=f"⚠️ {quality.get('reason', '输入无效')}\n\n💡 {quality.get('suggestion', '请描述具体的行为表现')}",
                author="系统"
            ).send()
            return
    
    if q == "complete":
        await run_full_reasoning(user_input)
    elif q == "partial":
        # 部分信息 → 智能判断：如果输入很长且包含具体细节，直接推理
        if len(user_input) > 150:
            await run_full_reasoning(user_input)
        else:
            await start_abc_guidance(user_input)
    else:
        # vague → ABC 教育（已在上面处理）
        await start_abc_education(user_input)


async def start_abc_education(user_input: str):
    """V6.3 新增：启动 ABC 教育"""
    session_id = cl.user_session.get("session_id") or "default"
    from abc_prompts import ABC_EDUCATION_INTRO, GUIDE_ANTECEDENT, QUESTION_ANTECEDENT
    
    # 记录用户输入
    log_interaction(session_id, "user", user_input, "vague_input")
    
    await cl.Message(
        content=ABC_EDUCATION_INTRO,
        author="系统"
    ).send()
    
    # 记录系统回复
    log_interaction(session_id, "assistant", ABC_EDUCATION_INTRO, "abc_education")
    
    # 初始化 ABC 状态
    abc_state = {
        "in_progress": True,
        "turn_count": 0,
        "max_turns": 5,
        "antecedent": None,
        "behavior": None,
        "consequence": None,
    }
    cl.user_session.set("abc_state", abc_state)
    
    guide_msg = GUIDE_ANTECEDENT.format(question=QUESTION_ANTECEDENT)
    await cl.Message(content=guide_msg, author="系统").send()
    
    # 记录系统回复
    log_interaction(session_id, "assistant", guide_msg, "guide_antecedent")


async def start_abc_guidance(user_input: str):
    """V6.3 新增：启动 ABC 引导"""
    session_id = cl.user_session.get("session_id") or "default"
    from abc_prompts import GUIDE_ANTECEDENT, QUESTION_ANTECEDENT
    
    # 记录用户输入
    log_interaction(session_id, "user", user_input, "partial_input")
    
    # 初始化 ABC 状态
    abc_state = {
        "in_progress": True,
        "turn_count": 0,
        "max_turns": 5,
        "antecedent": None,
        "behavior": None,
        "consequence": None,
    }
    cl.user_session.set("abc_state", abc_state)
    
    guide_msg = GUIDE_ANTECEDENT.format(question=QUESTION_ANTECEDENT)
    await cl.Message(content=guide_msg, author="系统").send()
    
    # 记录系统回复
    log_interaction(session_id, "assistant", guide_msg, "guide_antecedent")


async def handle_abc_guidance(user_input: str, abc_state: dict):
    """V6.4.2 优化：智能提取 ABC 信息，避免机械追问"""
    session_id = cl.user_session.get("session_id") or "default"
    from abc_prompts import (
        CONFIRM_ANTECEDENT, GUIDE_BEHAVIOR, QUESTION_BEHAVIOR,
        CONFIRM_BEHAVIOR, GUIDE_CONSEQUENCE, QUESTION_CONSEQUENCE,
        CONFIRM_CONSEQUENCE
    )
    
    abc_state["turn_count"] += 1
    
    # 记录用户输入
    log_interaction(session_id, "user", user_input, f"abc_turn_{abc_state['turn_count']}")
    
    # 弹性上限
    if abc_state["turn_count"] > abc_state["max_turns"]:
        await generate_partial_report(abc_state)
        return
    
    # 智能判断：用户是否一次性提供了完整内容？
    if len(user_input) > 80 and not abc_state.get("antecedent"):
        # 用户一次性提供了完整描述，直接推理
        cl.user_session.set("abc_state", None)
        await run_full_reasoning(user_input)
        return
    
    # 按 A→B→C 顺序处理
    if not abc_state.get("antecedent"):
        abc_state["antecedent"] = user_input
        content = CONFIRM_ANTECEDENT.format(value=user_input)
        content += "\n" + GUIDE_BEHAVIOR.format(question=QUESTION_BEHAVIOR)
        cl.user_session.set("abc_state", abc_state)
        await cl.Message(content=content, author="系统").send()
        log_interaction(session_id, "assistant", content, "confirm_a_guide_b")
    
    elif not abc_state.get("behavior"):
        # 智能检测：用户是否在回答 B 时已经包含了 C 的信息？
        abc_state["behavior"] = user_input
        
        # 检测是否包含后果相关信息（家长的处理方式和结果）
        # 使用更强的关键词组合检测，避免误判
        consequence_indicators = [
            # 处理方式相关
            "处理方式", "怎么处理", "怎么做的", "我的反应", "我一般", "我就会",
            # 具体行动
            "退让", "不让步", "不让", "退一步", "安慰", "安抚", "哄",
            "发脾气", "生气", "克制", "控制", "说不想", "想发脾",
            # 结果描述
            "最后", "然后他", "后来", "结果", "之后",
        ]
        
        # 统计匹配的关键词数量
        matched_count = sum(1 for kw in consequence_indicators if kw in user_input)
        
        # 如果匹配 2 个及以上关键词，说明用户很可能已经提供了 C 的信息
        if matched_count >= 2:
            # 用户已经提供了 C 的信息，智能提取
            abc_state["consequence"] = user_input
            cl.user_session.set("abc_state", abc_state)
            
            # 确认并直接进入推理
            confirm_msg = CONFIRM_CONSEQUENCE.format(
                antecedent=abc_state["antecedent"],
                behavior=abc_state["behavior"],
                consequence=user_input
            )
            await cl.Message(content=confirm_msg, author="系统").send()
            log_interaction(session_id, "assistant", confirm_msg, "confirm_all_start_reasoning")
            
            # 清除引导状态
            cl.user_session.set("abc_state", None)
            
            # 用自然语言拼接已收集的 ABC
            combined = f"前因：{abc_state['antecedent']}。行为：{abc_state['behavior']}。后果：{user_input}。"
            await run_full_reasoning(combined)
        else:
            # 用户只提供了 B，继续询问 C
            content = CONFIRM_BEHAVIOR.format(value=user_input)
            content += "\n" + GUIDE_CONSEQUENCE.format(question=QUESTION_CONSEQUENCE)
            cl.user_session.set("abc_state", abc_state)
            await cl.Message(content=content, author="系统").send()
            log_interaction(session_id, "assistant", content, "confirm_b_guide_c")
    
    elif not abc_state.get("consequence"):
        abc_state["consequence"] = user_input
        cl.user_session.set("abc_state", abc_state)
        
        # ABC 收集完成 → 过渡声明 + 触发推理
        confirm_msg = CONFIRM_CONSEQUENCE.format(
            antecedent=abc_state["antecedent"],
            behavior=abc_state["behavior"],
            consequence=abc_state["consequence"]
        )
        await cl.Message(content=confirm_msg, author="系统").send()
        log_interaction(session_id, "assistant", confirm_msg, "confirm_all_start_reasoning")
        
        # 清除引导状态
        cl.user_session.set("abc_state", None)
        
        # 用自然语言拼接已收集的 ABC
        combined = f"前因：{abc_state['antecedent']}。行为：{abc_state['behavior']}。后果：{abc_state['consequence']}。"
        await run_full_reasoning(combined)
    
    else:
        # 理论上不会到这里
        await generate_partial_report(abc_state)


async def generate_partial_report(abc_state: dict):
    """V6.3 新增：基于已有信息生成降级报告"""
    from abc_prompts import TRANSITION_PARTIAL
    
    cl.user_session.set("abc_state", None)
    
    await cl.Message(content=TRANSITION_PARTIAL, author="系统").send()
    
    parts = []
    if abc_state.get("antecedent"):
        parts.append(f"前因：{abc_state['antecedent']}")
    if abc_state.get("behavior"):
        parts.append(f"行为：{abc_state['behavior']}")
    if abc_state.get("consequence"):
        parts.append(f"后果：{abc_state['consequence']}")
    
    combined = "\n".join(parts) if parts else "用户提供了部分行为观察信息"
    await run_full_reasoning(combined)


async def run_full_reasoning(user_input: str):
    """V6.4.2 重构：推理过程可折叠 + 进度提示 + 中台数据记录"""
    session_id = cl.user_session.get("session_id") or "default"
    start_time = time.time()
    
    # 记录用户输入
    log_conversation(session_id, "user", user_input)

    thinking_parts = []
    assistant_response = ""
    scene_type = ""
    hypothesis = ""

    try:
        # 发送进度消息
        progress_msg = cl.Message(content="", author="推理引擎")
        await progress_msg.stream_token("🤔 正在分析中...")

        # Step 1: 场景识别
        await progress_msg.stream_token("\n🔍 Step 1: 场景识别")
        step1_result = await engine.step1_scene_recognition(user_input)
        scene_name = step1_result.get("scene_name", "未知场景")
        scene_type = step1_result.get("scene_type", "")
        core_challenge = step1_result.get("core_challenge", "")
        thinking_parts.append(f"📌 识别场景：[{scene_type}] {scene_name}\n💡 核心挑战：{core_challenge}")
        
        # Step 2: 假设生成
        await progress_msg.stream_token("\n🧠 Step 2: 假设生成")
        step2_result = await engine.step2_hypothesis_generation(user_input, step1_result)
        hypotheses = step2_result.get("hypotheses", [])
        hyp_text = ""
        for h in hypotheses:
            h_id = h.get("id", "?")
            hypothesis_text = h.get("content", "")
            confidence = h.get("confidence", 0)
            label = engine.confidence_label(confidence)
            reason = h.get("reason", "")
            hyp_text += f"\n### 假设 {h_id}（{label}）\n{hypothesis_text}"
            if reason:
                hyp_text += f"\n> 理由：{reason}"
            if not hypothesis:
                hypothesis = h_id  # 记录主要假设
        thinking_parts.append(hyp_text)
        
        # Step 3: 证据检验
        await progress_msg.stream_token("\n🔬 Step 3: 证据检验")
        step3_result = engine._get_evidence_from_hypotheses(hypotheses)
        evidence_items = step3_result.get("evidence_examination", [])
        ev_text = ""
        for ev in evidence_items:
            h_id = ev.get('hypothesis_id', '?')
            decision = ev.get("decision", "保留")
            supporting = ev.get("supporting_evidence", [])
            ev_text += f"\n- **假设 {h_id}** → ✅ {decision}"
            if supporting:
                ev_text += f"\n  支持证据：{supporting[0] if supporting else '无'}"
        thinking_parts.append(ev_text)
        
        # Step 4: 机制解释
        await progress_msg.stream_token("\n💡 Step 4: 机制解释")
        step4_result = await engine.step4_mechanism_explanation(user_input, step1_result, step3_result)
        mech_text = ""
        cognitive_mechanism = step4_result.get("cognitive_mechanism", "")
        metaphor = step4_result.get("metaphor", "")
        developmental_perspective = step4_result.get("developmental_perspective", "")
        if cognitive_mechanism:
            mech_text += f"\n🔬 认知机制：{cognitive_mechanism}"
        if metaphor:
            mech_text += f"\n🎭 比喻解释：{metaphor}"
        if developmental_perspective:
            mech_text += f"\n📈 发展视角：{developmental_perspective}"
        thinking_parts.append(mech_text)
        
        # Step 5: 干预策略
        await progress_msg.stream_token("\n🎯 Step 5: 干预策略")
        step5_result = await engine.step5_intervention_planning(user_input, step4_result)
        strategies = step5_result.get("intervention_strategies", [])
        strat_text = ""
        for s in strategies:
            strategy_name = s.get("name", "")
            description = s.get("description", "")
            why_effective = s.get("why_effective", "")
            strat_text += f"\n### {strategy_name}\n{description}"
            if why_effective:
                strat_text += f"\n> 💡 为什么有效：{why_effective}"
        thinking_parts.append(strat_text)
        
        await progress_msg.stream_token("\n📊 生成报告...")
        await progress_msg.send()
        
        # 组装可折叠的推理过程（HTML，需 unsafe_allow_html=true）
        thinking_content = "\n\n".join(thinking_parts)
        collapsed_thinking = f"""<details style="margin-bottom: 16px; border: 1px solid #e0e0e0; border-radius: 8px; padding: 8px 12px;">
<summary style="cursor: pointer; color: #999; font-size: 0.85em; font-weight: 500;">🧠 推理过程（点击查看）</summary>
<div style="color: #888; font-size: 0.82em; margin-top: 12px; line-height: 1.7; padding: 8px; background: #fafafa; border-radius: 6px;">

{thinking_content}

</div>
</details>"""
        
        # 生成完整报告
        full_result = {
            "step1": step1_result,
            "step2": step2_result,
            "step3": step3_result,
            "step4": step4_result,
            "step5": step5_result
        }
        report_html = engine.generate_report(full_result)
        
        # 合并：折叠的推理过程 + 正文报告
        final_content = collapsed_thinking + "\n\n" + report_html
        assistant_response = report_html  # 记录报告内容
        
        await cl.Message(
            content=final_content,
            author="分析报告"
        ).send()
        
        # 记录助手回答到中台（包含场景类型和假设）
        response_time = time.time() - start_time
        log_conversation(session_id, "assistant", assistant_response, scene_type, hypothesis, response_time)
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        await cl.Message(
            content=f"❌ 推理过程出错：{str(e)}\n\n```\n{error_detail}\n```",
            author="系统"
        ).send()
        
        # 记录错误到中台
        response_time = time.time() - start_time
        log_conversation(session_id, "assistant", f"错误：{str(e)}", scene_type, hypothesis, response_time)
