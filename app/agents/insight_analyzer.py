"""
洞察分析器 V3.0 - V4.5.13 个性化报告版
从"行为分类"升级为"共情洞察"

核心理念：
- 不是输出标签，而是生成洞察
- 不是事实复述，而是行为理解
- 不是专业术语，而是家长能懂的"金句"

V4.5.13 新增：
- 家长用语风格检测（专业 vs 日常）
- 个性化报告语言调整
- 详细版/简洁版选项
"""

import json
import logging
import re
from typing import Optional, Dict, Any

from app.llm.base import LLMClient

logger = logging.getLogger(__name__)


# ========== V4.5.13 P1-03: 家长用语风格检测 ==========
class ParentStyleDetector:
    """家长用语风格检测器"""
    
    # 专业术语关键词
    PROFESSIONAL_TERMS = [
        "前因", "后果", "强化", "消退", "ABC", "功能分析",
        "行为功能", "逃避", "寻求关注", "感觉统合", "感统",
        "刻板行为", "自我刺激", "提示", "辅助", "泛化",
        "工作记忆", "执行功能", "注意力缺陷", "感统失调"
    ]
    
    # 日常用语关键词
    CASUAL_TERMS = [
        "之前", "然后", "之后", "奖励", "不理", "什么时候",
        "老是", "总是", "就是", "好像", "感觉", "觉得",
        "孩子他", "我家", "老师他", "不知道咋办"
    ]
    
    @classmethod
    def detect_style(cls, conversation_history: list) -> str:
        """
        检测家长用语风格
        
        Args:
            conversation_history: 对话历史
            
        Returns:
            "professional" (专业) 或 "casual" (日常)
        """
        all_text = " ".join([
            msg.get("text", "") 
            for msg in conversation_history 
            if msg.get("role") == "user"
        ])
        
        prof_count = sum(1 for term in cls.PROFESSIONAL_TERMS if term in all_text)
        casual_count = sum(1 for term in cls.CASUAL_TERMS if term in all_text)
        
        # 句子长度和复杂度
        sentences = [s.strip() for s in re.split(r'[。！？!?]', all_text) if s.strip()]
        avg_sentence_length = sum(len(s) for s in sentences) / len(sentences) if sentences else 0
        
        style = "professional" if prof_count > casual_count else "casual"
        
        # 长句子 + 专业术语 → 更可能是专业人士
        if avg_sentence_length > 30 and prof_count >= 2:
            style = "professional"
        
        logger.info(f"📊 家长用语风格检测：{style} (专业术语={prof_count}, 日常用语={casual_count}, 平均句长={avg_sentence_length:.1f})")
        return style
    
    @classmethod
    def get_style_prompt_suffix(cls, style: str) -> str:
        """
        根据风格返回 Prompt 后缀
        
        Args:
            style: 用语风格 ("professional" 或 "casual")
            
        Returns:
            Prompt 后缀
        """
        if style == "professional":
            return """
【语言风格要求】
- 使用专业术语（如"前因"、"后果"、"强化"、"功能分析"）
- 保持专业严谨，但要有温度
- 可以适当使用专业概念解释
- 长度：详细版（150-200 字）"""
        else:
            return """
【语言风格要求】
- 使用日常语言，避免专业术语
- 用"之前/然后/之后"代替"前因/后果"
- 用"奖励"代替"强化"，用"不理"代替"消退"
- 多用比喻和金句，说进家长心坎里
- 长度：简洁版（80-120 字）"""


class InsightAnalyzer:
    """
    洞察分析器 V3.0
    
    三步推理链：
    1. 功能判断（内在逻辑）- 不直接输出术语
    2. 深度归因（动机与能力）- 区分"不想做"vs"做不到"
    3. 提炼核心洞察 - 给家长的"金句"
    """

    # V4.5.7 分析 Prompt - 矛盾证据优先处理版
    ANALYSIS_SYSTEM_PROMPT = """你是一位经验丰富的 BCBA 督导，正在将观察转化为对家长有启发的洞察。

你的任务是：
1. 进行专业的"专家拆解"（内部分析）- 精准判断功能
2. 将专业分析"翻译"成家长能懂的语言（对外沟通）- 有温度、有观点
3. 展现临床鉴别思考过程 - 说明为什么排除其他可能性

【P0 关键规则 - 矛盾证据优先处理】
当用户描述中出现以下"能力完备"关键词时，必须优先处理：
- 关键词："都会做"、"已经会"、"自己能"、"不需要帮助"、"能做好"
- 处理规则：
  1. 立即降低"提示依赖"假设置信度至 30% 以下
  2. 立即提升"寻求关注"或"获得社会性确认"假设置信度至 70% 以上
  3. 在鉴别诊断中明确说明："由于孩子具备完成任务的能力，'叫家长'行为的主要功能更可能是获取关注而非获取提示"

【关键分析原则 - 寻求关注鉴别】
当行为模式满足以下特征时，应判断为"寻求关注"而非"提示依赖"：
- 孩子在成人注意力分散时（打电话、招待客人）故意制造问题行为
- 关键线索："其实都会做"、"不需要帮助就能完成" → 排除提示依赖（P0 规则）
- 行为目的：获取成人注意力，而非获取任务执行提示
- 能力缺口：恰当的社交沟通技能（如何用适当方式获取关注）
- 鉴别性问题："他叫您的时候，主要是需要您帮助解题，还是只是想让您看看他？"

【关键分析原则 - 社交技能不足鉴别】（V4.5.20 P2 新增）
当行为模式满足以下特征时，应判断为"社交技能不足"而非"寻求关注"或"提示依赖"：
- **身体边界感不足**：拥抱不知轻重、靠得太近、触碰他人过度用力
- **观点采择困难**：难以理解他人感受、坚持己见、无法接受"各自当队长"等折中方案
- **社交灵活性差**：规则僵化、"只能我当"、难以轮流等待、无法适应变化
- **情绪识别困难**：看不出别人不高兴、读不懂面部表情或肢体语言
- **关键线索**：行为发生在**同伴互动**场景中（而非成人 - 儿童互动）
- **能力缺口**：换位思考、情绪识别、社交灵活性、身体感知
- **干预方向**：直接教学（社交故事、角色扮演、视觉提示），而非行为管理
- **鉴别性问题**："孩子是'想要关注但不知道如何恰当获取'，还是'根本没意识到别人的感受'？"

【优先级规则 - V4.5.20 P2】
1. **社交技能不足 > 寻求关注**：如果行为发生在同伴互动中，且表现为身体边界感不足或观点采择困难，优先判断为社交技能不足
2. **能力缺口 > 行为功能**：如果能力缺口明确指向"换位思考"、"社交灵活性"等，干预必须是技能教学，而非行为管理
3. **场景优先**：同伴互动场景 → 社交技能；成人 - 儿童互动 → 寻求关注/提示依赖

【关键分析原则 - 提示依赖鉴别】
当行为模式表现为"有提示则执行，无提示则中断/发呆"，且任务具有明确的社会性目标时：
- 首要功能假设应从"自动强化"修正为"在提示依赖下的逃避（任务失败/认知负荷）"
- 这是特殊形式的"逃避"——逃避的是因提示中断而导致的"任务执行失败"或"认知过载"
- 能力缺口：工作记忆（记不住多步骤序列）和持续性注意（无法在提示间隙自我维持任务表征）
- 环境整合：嘈杂、拥挤等环境因素会加剧对单一、清晰视觉提示的依赖

【临床鉴别思考要求 - V4.10.0 P1 专业版】
在生成报告时，鉴别诊断部分必须包含明确的排除理由，并严格遵循以下三模块结构：

【鉴别诊断结构要求 - V4.10.0 P1 强制】
**必须**包含以下三个子模块，缺一不可：

**1. 鉴别与排除**（临床推理过程）
- 格式：使用"为何不是 XXX"的明确排除句式
- 内容：针对至少 2 个竞争性假设，说明排除理由
- 示例：
  • 为何不是"提示依赖"：行为是自发、主动的，并非由他人提示才启动
  • 为何不是"寻求关注"：行为指向游戏本身，而非为了获得成人的注意或反应

**2. 核心假设**（专业概括）
- 格式：用专业术语命名行为模式
- 内容：一句话概括核心行为模式 + 简要解释
- 示例：游戏参与中的"社交 - 认知僵化"。即在快速变化的社交情境中，难以整合外界信息（他人的规则、反应）来更新自己的认知和行为脚本。

**3. 能力缺口分析**（从现象到归因）
- 格式：每个缺口必须包含"现象→归因"的完整链条
- 内容：从具体行为表现推导出 2-3 个最关键的能力缺口
- 示例：
  1. 社交信号监测弱："以为别人在和她玩"→表明在监测他人是否在回应自己、游戏是否同步这一关键社交信号上存在困难
  2. 认知灵活性不足："规则只有 3 条，不停重复"→表明难以处理复杂的、多变的群体规则
  3. 观点采择应用困难：在游戏高潮中，难以快速推断"其他小朋友现在在想什么"

【语言风格要求】
- ✅ 推荐：使用专业术语但通过比喻使其易懂（如"脚手架""社交监测"）
- ✅ 推荐：每点能力缺口都紧扣现象证据（如"'以为别人在和她玩'→表明在监测他人是否在回应自己上存在困难"）
- ❌ 避免："我们觉得""从...来看"等冗余口语化表述
- ❌ 避免：引入与现象关联性不强的能力（如"工作记忆"但无证据支持）
- ❌ 避免：只说结论不展示推理过程（如"支持证据：基于您的详细描述"）

【核心洞察要求 - V4.5.21 优化版】
- ❌ 避免：通用比喻（如"社交雷达"、"像手机需要充电"），缺乏针对性
- ❌ 避免：抽象表述（如"孩子不是故意捣乱"）
- ✅ 推荐：结合具体行为细节和孩子名字（如果有），如"玥玥不是故意要弄哭小朋友，她只是还没学会怎么控制拥抱的力量"
- ✅ 推荐：用能力发展视角，如"这个技能还在发展中，需要练习"
- 核心原则：用孩子的具体行为举例，让家长感觉"这就是在说我家孩子"，而不是"这是在说所有孩子"

【语言风格要求 - V4.5.21 新增】
- 用短句，避免长句（每句<30 字）
- 用"我们"而不是"您"，拉近距离
- 用具体例子，不用抽象概念
- 用"还没学会"而不是"不会"，强调发展视角
- 用"练习"而不是"训练"，减少压力感

【V4.10.0 P1 字段兼容性要求】
请严格按照以下 JSON 格式输出，确保所有字段都存在：
{
    "functional_judgment": "首要功能判断，如'提示依赖下的逃避'、'逃避难度任务'、'寻求关注'、'社交技能不足'等",
    "core_insight": "结合具体行为细节的个性化洞察，避免通用比喻。例如：'玥玥不是故意要弄哭小朋友，她只是还没学会怎么控制拥抱的力量'",
    "capability_hypothesis": "这可能反映了哪方面的能力挑战，如'工作记忆和持续性注意方面的挑战'或'社交信号监测与认知灵活性的挑战'",
    "clinical_differential": "必须包含三模块结构，用 Markdown 格式，注意编号层级：\n\n1. **鉴别与排除**：\n   • 为何不是'提示依赖'：[具体理由]\n   • 为何不是'社交技能不足'：[具体理由]\n\n2. **核心假设**：[专业术语命名 + 简要解释]\n\n3. **能力缺口分析**：\n   • **[缺口名称]**：'[行为原文]'→[能力归因]\n   • **[缺口名称]**：'[行为原文]'→[能力归因]\n\n注意：主标题必须用 1. 2. 3. 编号，能力缺口分析子项必须用 • 符号。",
    "intervention_principle": "针对最可能的假设，提出具体的干预原则，如'将外部提示转化为内部提示'或'建立社交信号监测的脚手架'",
    "expert_breakdown": {
        "behavior_pattern": "一句话命名该行为模式",
        "functional_hypothesis": "功能假设详细说明",
        "capability_gap": "能力缺口分析",
        "contextual_factors": "环境因素如何影响行为"
    },
    "core_insight_for_parent": "与 core_insight 相同的核心洞察",
    "strategy_principle": "与 intervention_principle 相同的干预原则",
    "reasoning_brief": "简短的专业推理（50 字以内）"
}

【V4.10.3 编号层级强制规则】
- **主标题编号**：1. 鉴别与排除 → 2. 核心假设 → 3. 能力缺口分析（必须用 1. 2. 3.）
- **子列表编号**：能力缺口分析内部必须用 • 符号，不能用 1. 2. 3.
- **能力缺口数量**：必须生成 2-3 个缺口，每个缺口必须有行为证据支撑
- **格式示例**：
  ```
  1. **鉴别与排除**：
     • 为何不是'提示依赖'：[理由]
     • 为何不是'社交技能不足'：[理由]
  
  2. **核心假设**：[内容]
  
  3. **能力缺口分析**：
     • **认知灵活性不足**：'[行为原文]'→[归因]
     • **情绪调节困难**：'[行为原文]'→[归因]
  ```
- **寻求关注场景的标准能力缺口**（当 functional_judgment 包含"关注"时）：
  • 社交沟通技能不足：'[发出奇怪声音]'→表明在如何用恰当方式获取成人注意力上存在困难
  • 社交信号监测弱：'[老师看她时她就笑]'→表明能监测到老师是否在关注自己...
  • 自我调节能力不足：'[即使被批评也停不下来]'→表明在兴奋/冲动时难以控制行为强度
- **禁止空泛表述**：如"相关技能待发展"、"需要进一步观察"等
"""

    ANALYSIS_USER_PROMPT_TEMPLATE = """请基于以下观察信息，进行专家拆解与共情翻译：

【观察信息】
- 环境：{environment}
- 情境：{antecedent}
- 孩子的表现：{behavior}
- 当时的回应：{consequence}

【你的分析任务】
1. **专家拆解（专业视角）**：
   - 识别模式：这是"有提示则执行，无提示则中断"的提示依赖行为吗？
   - 功能判断：如果是，主要功能是"提示依赖下的逃避"而非"自动强化"
   - 能力缺口：工作记忆和/或持续性注意的挑战
   - 环境因素：环境如何加剧了对视觉提示的依赖

2. **共情翻译（家长视角）**：
   - 核心洞察：用"金句"直击本质，说进家长心坎里
   - 干预原则："将外部提示转化为内部提示"

【V4.5.20 P2 新增 - 社交技能不足检查】
如果行为发生在**同伴互动**场景中（如与玩伴玩耍、争抢角色、拥抱互动等），且表现为：
- 身体边界感不足（拥抱不知轻重、靠得太近）
- 观点采择困难（难以理解他人感受、坚持己见）
- 社交灵活性差（规则僵化、难以轮流等待）
→ 应判断为"社交技能不足"，而非"寻求关注"
→ 能力缺口：换位思考、情绪识别、社交灵活性
→ 干预原则：直接教学（社交故事、角色扮演、视觉提示）

请输出 JSON 格式的分析结果。"""

    # V3.6 鉴别诊断分析 Prompt - 临床深度增强版
    ANALYSIS_WITH_DIFFERENTIAL_TEMPLATE = """请基于以下观察信息和竞争性假设，进行鉴别诊断分析：

【观察信息】
- 环境：{environment}
- 情境：{antecedent}
- 孩子的表现：{behavior}
- 当时的回应：{consequence}
- 用户补充的鉴别细节：{discriminating_answer}

【竞争性假设】
{hypotheses_json}

【你的分析任务】
请参考提供的专业假设，根据所有信息评估每种假设的可能性：
1. 逐一评估每个假设的支持证据和不支持证据
2. 给出一个综合性的、有层次的分析：哪个假设可能性最高，为什么
3. 同时考虑其他假设是否可能部分存在
4. 基于最可能的假设，给出核心洞察和干预原则
5. 生成临床鉴别思考：说明鉴别诊断过程

请严格按照以下 JSON 格式输出：
{{
    "expert_breakdown": {{
        "behavior_pattern": "一句话命名该行为模式",
        "functional_hypothesis": "基于鉴别诊断，判断最可能的功能，并说明推理",
        "capability_gap": "分析这可能反映了哪方面的能力挑战",
        "contextual_factors": "简述环境因素如何影响行为",
        "differential_reasoning": "简述鉴别诊断过程：为什么 HX 可能性最高，其他假设的可能性如何"
    }},
    "clinical_differential": "针对观察到的行为，说明临床上通常考虑的几种可能性（参考竞争性假设），然后结合当前观察信息（如用户的鉴别细节）说明为什么某种可能性最高。100-200 字。",
    "core_insight_for_parent": "基于专家拆解，用一句'金句'直击本质，说进家长心坎里",
    "strategy_principle": "针对最可能的假设，提出具体的干预原则",
    "reasoning_brief": "简短的专业推理（50 字以内）"
}}"""

    def __init__(self, llm_client: LLMClient):
        """
        初始化洞察分析器

        Args:
            llm_client: LLM 客户端实例
        """
        self.llm = llm_client
        logger.info("InsightAnalyzer V3.0 初始化完成")

    def analyze(self, environment: str, antecedent: str, behavior: str, consequence: str, competing_hypotheses: Optional[list] = None, discriminating_answer: str = "", conversation_history: Optional[list] = None, report_style: Optional[str] = None) -> dict:
        """
        执行三步推理分析（V4.5.13 - 个性化报告版）

        Args:
            environment: 环境上下文
            antecedent: 情境（前因）
            behavior: 孩子的表现（行为）
            consequence: 当时的回应（后果）
            competing_hypotheses: 竞争性假设列表（可选）
            discriminating_answer: 用户对鉴别性问题的回答（可选）
            conversation_history: 对话历史（用于检测家长用语风格）
            report_style: 报告风格 ("professional"/"casual"，不传则自动检测)

        Returns:
            洞察分析结果
        """
        logger.info(f"开始洞察分析：环境={environment[:30] if environment else '无'}, 情境={antecedent[:30]}..., 行为={behavior[:30]}...")
        
        # V4.5.13 新增：检测家长用语风格
        if report_style is None and conversation_history:
            report_style = ParentStyleDetector.detect_style(conversation_history)
        elif report_style is None:
            report_style = "casual"  # 默认日常风格
        
        style_suffix = ParentStyleDetector.get_style_prompt_suffix(report_style)
        logger.info(f"📝 报告风格：{report_style}")

        # V3.4 新增：如果有竞争性假设，使用鉴别诊断 Prompt
        if competing_hypotheses and discriminating_answer:
            user_prompt = self.ANALYSIS_WITH_DIFFERENTIAL_TEMPLATE.format(
                environment=environment or '未提及',
                antecedent=antecedent,
                behavior=behavior,
                consequence=consequence,
                hypotheses_json=json.dumps(competing_hypotheses, ensure_ascii=False, indent=2),
                discriminating_answer=discriminating_answer,
            ) + style_suffix
        else:
            user_prompt = self.ANALYSIS_USER_PROMPT_TEMPLATE.format(
                environment=environment or '未提及',
                antecedent=antecedent,
                behavior=behavior,
                consequence=consequence,
            ) + style_suffix

        try:
            result = self.llm.generate_json(
                system_prompt=self.ANALYSIS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=800,
            )

            # V4.3 核心修复：确保所有必需字段存在，进行数据转换和兼容
            result = self._ensure_v43_compatibility(result)
            
            # V4.10.3 新增：强制转换能力缺口分析的有序列表为无序列表
            logger.info(f"V4.10.3 修复前 clinical_differential: {result.get('clinical_differential', '')}")
            result = self._fix_capability_gap_format(result)
            logger.info(f"V4.10.3 修复后 clinical_differential: {result.get('clinical_differential', '')}")

            logger.info(f"洞察分析完成：{result['core_insight'][:50]}...")
            return result

        except Exception as e:
            logger.error(f"洞察分析失败：{e}")
            return self._get_fallback_result(str(e))
    
    def _fix_capability_gap_format(self, result: dict) -> dict:
        """
        V4.10.3 新增：强制修复 clinical_differential 的编号层级
        
        问题：
        1. LLM 经常忽略 Prompt 要求，三个主标题都用"1."
        2. 能力缺口分析的子列表用 1. 2. 3. 而不是 •
        3. 标题可能没有加粗标记（如"1. 鉴别与排除："而非"1. **鉴别与排除**："）
        
        解决：后处理强制修复编号层级，兼容有无加粗两种情况
        
        期望格式：
        1. **鉴别与排除**：
           • 为何不是...
        
        2. **核心假设**：...
        
        3. **能力缺口分析**：
           • **缺口 1**：...
           • **缺口 2**：...
        
        Args:
            result: LLM 返回的分析结果
            
        Returns:
            修复后的结果
        """
        clinical_diff = result.get("clinical_differential", "")
        if not clinical_diff:
            return result
        
        import re
        
        # ========== 修复 1: 主标题编号 ==========
        # 匹配模式：行首 + 数字 + "."或"、" + 空格 + 可选的 ** + 标题文本 + 可选的 **
        # 替换为正确的 1. 2. 3. 编号
        
        # 找到三个主标题的位置
        titles = ["鉴别与排除", "核心假设", "能力缺口分析"]
        lines = clinical_diff.split('\n')
        fixed_lines = []
        title_index = 0
        
        for line in lines:
            fixed_line = line
            # 检查是否是主标题行（行首有数字编号 + 标题，兼容有无加粗）
            # 正则：行首 + 数字 + .或、 + 可选空格 + 可选** + 捕获标题文本 + 可选** + 可选冒号
            title_match = re.match(r'^(\d+)[.、]\s*\*?([^*:]+)\*?\s*:?\s*$', line.strip())
            if title_match:
                # 检查是否是我们期望的三个标题之一
                title_text = title_match.group(2).strip()
                if title_text in titles and title_index < len(titles):
                    # 用正确的编号替换
                    correct_num = title_index + 1
                    # 保持原有格式（有无加粗都保留）
                    fixed_line = re.sub(r'^\d+[.、]', f'{correct_num}.', line)
                    title_index += 1
            
            fixed_lines.append(fixed_line)
        
        clinical_diff = '\n'.join(fixed_lines)
        
        # ========== 修复 2: 能力缺口分析的子列表 ==========
        # 找到"能力缺口分析"部分，将其中的有序列表转换为无序列表
        if "能力缺口分析" in clinical_diff:
            parts = clinical_diff.split("能力缺口分析")
            if len(parts) >= 2:
                prefix = parts[0] + "能力缺口分析"
                suffix = parts[1]
                
                # 只替换能力缺口分析内部的有序列表（有缩进 + 可选加粗）
                # 匹配：换行 + 空格 + 数字 + 点 + 空格 + 可选** + 内容 + 可选**
                suffix_fixed = re.sub(r'\n\s+(\d+)[.、]\s*\*?([^\n]+?)\*?\s*$', r'\n   • \2', suffix, flags=re.MULTILINE)
                
                clinical_diff = prefix + suffix_fixed
        
        result["clinical_differential"] = clinical_diff
        
        logger.info(f"V4.10.3 clinical_differential 编号层级修复完成")
        return result
    
    def _ensure_v43_compatibility(self, result: dict) -> dict:
        """
        V4.3 核心修复：确保返回字段与 V4.3 报告模板完全兼容
        
        数据转换逻辑：
        1. 确保 functional_judgment, core_insight, capability_hypothesis 存在
        2. 兼容旧字段名（expert_breakdown → functional_judgment 等）
        3. 填充缺失字段的默认值
        """
        # 1. 确保核心字段存在
        if "functional_judgment" not in result:
            # 尝试从 expert_breakdown 推断
            expert = result.get("expert_breakdown", {})
            result["functional_judgment"] = expert.get("functional_hypothesis", "提示依赖下的逃避")
        
        if "core_insight" not in result:
            # 尝试从 core_insight_for_parent 复制
            result["core_insight"] = result.get("core_insight_for_parent", "孩子正在用这种方式表达他的需求。")
        
        if "capability_hypothesis" not in result:
            # 尝试从 expert_breakdown 复制
            expert = result.get("expert_breakdown", {})
            result["capability_hypothesis"] = expert.get("capability_gap", "工作记忆和持续性注意方面的挑战。")
        
        # 2. 确保 clinical_differential 存在
        if "clinical_differential" not in result:
            result["clinical_differential"] = "基于观察到的行为模式，我们考虑了多种可能性，结合关键信息判断最可能的功能假设。"
        
        # 3. 确保 intervention_principle 存在
        if "intervention_principle" not in result:
            result["intervention_principle"] = result.get("strategy_principle", "将外部提示转化为内部提示")
        
        # 4. 确保 expert_breakdown 存在（向后兼容）
        if "expert_breakdown" not in result:
            result["expert_breakdown"] = {
                "behavior_pattern": "待分析行为模式",
                "functional_hypothesis": result.get("functional_judgment", ""),
                "capability_gap": result.get("capability_hypothesis", ""),
                "contextual_factors": "环境因素影响待评估"
            }
        
        # 5. 确保 core_insight_for_parent 与 core_insight 一致（向后兼容）
        if "core_insight_for_parent" not in result:
            result["core_insight_for_parent"] = result["core_insight"]
        
        # 6. 确保 strategy_principle 与 intervention_principle 一致（向后兼容）
        if "strategy_principle" not in result:
            result["strategy_principle"] = result["intervention_principle"]
        
        # 7. 确保 reasoning_brief 存在
        if "reasoning_brief" not in result:
            result["reasoning_brief"] = "基于 ABC 模式和临床经验的综合判断"
        
        logger.info(f"V4.3 字段兼容性检查完成：functional_judgment={result.get('functional_judgment', 'N/A')[:30]}...")
        return result
    
    def _get_fallback_result(self, error: str) -> dict:
        """
        V4.3 降级方案：当分析失败时返回完整的兼容结构
        """
        return {
            "functional_judgment": "inconclusive",
            "core_insight": "孩子正在用这种方式表达他的需求或感受。",
            "capability_hypothesis": "相关技能还在发展中，需要我们的耐心支持。",
            "clinical_differential": "由于信息有限，无法进行详细的鉴别诊断。建议继续观察并收集更多信息。",
            "intervention_principle": "提供温和、一致的支持，观察孩子的反应模式。",
            "expert_breakdown": {
                "behavior_pattern": "待分析行为模式",
                "functional_hypothesis": "需要更多信息进行判断",
                "capability_gap": "相关技能还在发展中",
                "contextual_factors": "环境因素影响待评估"
            },
            "core_insight_for_parent": "孩子正在用这种方式表达他的需求或感受。",
            "strategy_principle": "提供温和、一致的支持，观察孩子的反应模式。",
            "reasoning_brief": f"分析过程出现异常：{error}",
        }
