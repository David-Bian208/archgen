"""心伴解读 Agent 核心实现"""

import logging
from typing import Dict, Any

from app.llm.base import LLMClient

try:
    from .models import HeartInterpretationInput, HeartInterpretationOutput
    from .prompt import SYSTEM_PROMPT, GENERATE_PROMPT
except ImportError:
    from models import HeartInterpretationInput, HeartInterpretationOutput
    from prompt import SYSTEM_PROMPT, GENERATE_PROMPT

logger = logging.getLogger(__name__)


class HeartInterpreterAgent:
    """心伴解读 Agent - 将专业分析转化为温暖解读"""
    
    def __init__(self, llm_client: LLMClient):
        """
        初始化心伴解读 Agent
        
        Args:
            llm_client: LLM 客户端实例
        """
        self.llm = llm_client
        logger.info("HeartInterpreterAgent 初始化完成")
    
    def interpret(self, input_data: Dict[str, Any]) -> HeartInterpretationOutput:
        """
        生成心伴解读
        
        Args:
            input_data: 输入数据字典
            
        Returns:
            心伴解读输出
        """
        logger.info(f"开始生成心伴解读：孩子={input_data.get('child_name', '未知')}")
        
        try:
            # 1. 构建输入模型
            input_model = self._build_input_model(input_data)
            
            # 2. 生成提示词
            user_prompt = self._generate_user_prompt(input_model)
            
            # 3. 调用 LLM
            response = self.llm.generate(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.7,  # 稍高温度，更有温度
                max_tokens=1500,
            )
            
            # 4. 解析响应
            output = self._parse_response(response, input_model)
            
            logger.info("心伴解读生成完成")
            return output
            
        except Exception as e:
            logger.error(f"心伴解读生成失败：{e}")
            return self._get_fallback_result(input_data)
    
    def _build_input_model(self, data: Dict[str, Any]) -> HeartInterpretationInput:
        """构建输入模型"""
        from .models import DevelopmentalProfile, HypothesisRanking
        
        # 构建发展画像
        profile = DevelopmentalProfile(
            strengths=data.get("strengths", []),
            current_focus=data.get("current_focus", []),
            potential_challenges=data.get("challenges", []),
        )
        
        # 构建假设优先级
        hypotheses = []
        for h in data.get("hypotheses_ranking", []):
            hypotheses.append(HypothesisRanking(
                id=h.get("id", ""),
                rank=h.get("rank", 0),
                confidence=h.get("confidence", 0.0),
                description=h.get("description", ""),
            ))
        
        return HeartInterpretationInput(
            developmental_profile=profile,
            attribution_statement=data.get("attribution", ""),
            hypotheses_ranking=hypotheses,
            identified_problems=data.get("identified_problems", []),
            child_name=data.get("child_name", "孩子"),
            child_age=data.get("child_age", "未明确"),
            parent_concerns=data.get("parent_concerns", []),
        )
    
    def _generate_user_prompt(self, input_model: HeartInterpretationInput) -> str:
        """生成用户提示词"""
        # 格式化假设优先级
        hypotheses_text = "\n".join([
            f"{h.rank}. {h.description} (置信度：{h.confidence:.2f})"
            for h in input_model.hypotheses_ranking
        ])
        
        # 格式化问题列表
        problems_text = "\n".join([f"- {p}" for p in input_model.identified_problems])
        
        # 格式化家长关注点
        concerns_text = "\n".join([f"- {c}" for c in input_model.parent_concerns]) or "未明确"
        
        return GENERATE_PROMPT.format(
            child_name=input_model.child_name,
            child_age=input_model.child_age,
            strengths=", ".join(input_model.developmental_profile.strengths) or "待补充",
            current_focus=", ".join(input_model.developmental_profile.current_focus) or "待补充",
            challenges=", ".join(input_model.developmental_profile.potential_challenges) or "待补充",
            attribution=input_model.attribution_statement,
            hypotheses_ranking=hypotheses_text,
            identified_problems=problems_text,
            parent_concerns=concerns_text,
        )
    
    def _parse_response(self, response: str, input_model: HeartInterpretationInput) -> HeartInterpretationOutput:
        """解析 LLM 响应"""
        # 简单解析：提取各个部分
        sections = self._extract_sections(response)
        
        # 构建完整文本
        full_text = self._build_full_text(sections)
        
        return HeartInterpretationOutput(
            emotional_anchor=sections.get("emotional_anchor", ""),
            developmental_map=sections.get("developmental_map", ""),
            priority_explanation=sections.get("priority_explanation", ""),
            intervention_principle=sections.get("intervention_principle", ""),
            intervention_scenes=sections.get("intervention_scenes", []),
            small_changes=sections.get("small_changes", []),
            progress_signals=sections.get("progress_signals", []),
            professional_support=sections.get("professional_support", ""),
            full_text=full_text,
        )
    
    def _extract_sections(self, text: str) -> Dict[str, Any]:
        """从响应中提取各个部分"""
        sections = {
            "emotional_anchor": "",
            "developmental_map": "",
            "priority_explanation": "",
            "intervention_principle": "",
            "intervention_scenes": [],
            "small_changes": [],
            "progress_signals": [],
            "professional_support": "",
        }
        
        # 简单提取：根据标题分割
        current_section = None
        current_content = []
        
        for line in text.split("\n"):
            line = line.strip()
            
            # 检测章节标题
            if "**情感锚点**" in line or "### 1" in line:
                current_section = "emotional_anchor"
                current_content = []
            elif "**发展地图**" in line or "### 2" in line:
                if current_section:
                    sections[current_section] = "\n".join(current_content)
                current_section = "developmental_map"
                current_content = []
            elif "**优先级解释**" in line or "### 3" in line:
                if current_section:
                    sections[current_section] = "\n".join(current_content)
                current_section = "priority_explanation"
                current_content = []
            elif "**核心理念**" in line or "### 4" in line:
                if current_section:
                    sections[current_section] = "\n".join(current_content)
                current_section = "intervention_principle"
                current_content = []
            elif "**具体场景**" in line or "### 5" in line:
                if current_section:
                    sections[current_section] = "\n".join(current_content)
                current_section = "intervention_scenes"
                current_content = []
            elif "**微小改变**" in line or "### 6" in line:
                if current_section:
                    sections[current_section] = "\n".join(current_content)
                current_section = "small_changes"
                current_content = []
            elif "**进步信号**" in line or "### 7" in line:
                if current_section == "small_changes":
                    sections["small_changes"] = current_content
                current_section = "progress_signals"
                current_content = []
            elif "**专业支持**" in line:
                if current_section == "progress_signals":
                    sections["progress_signals"] = current_content
                current_section = "professional_support"
                current_content = []
            elif current_section and line:
                current_content.append(line)
        
        # 保存最后一个部分
        if current_section:
            if current_section in ["intervention_scenes", "small_changes", "progress_signals"]:
                sections[current_section] = current_content
            else:
                sections[current_section] = "\n".join(current_content)
        
        return sections
    
    def _build_full_text(self, sections: Dict[str, Any]) -> str:
        """构建完整文本"""
        parts = []
        
        # 1. 情感锚点
        if sections.get("emotional_anchor"):
            parts.append(f"## 💖 我们觉得\n{sections['emotional_anchor']}\n")
        
        # 2. 发展地图
        if sections.get("developmental_map"):
            parts.append(f"## 🗺️ 发展地图\n{sections['developmental_map']}\n")
        
        # 3. 优先级解释
        if sections.get("priority_explanation"):
            parts.append(f"## 🎯 优先解决的卡点\n{sections['priority_explanation']}\n")
        
        # 4. 核心理念
        if sections.get("intervention_principle"):
            parts.append(f"## 💡 核心理念\n{sections['intervention_principle']}\n")
        
        # 5. 具体场景
        if sections.get("intervention_scenes"):
            scenes = "\n".join([f"- {s}" for s in sections["intervention_scenes"]])
            parts.append(f"## 🎮 具体场景\n{scenes}\n")
        
        # 6. 微小改变
        if sections.get("small_changes"):
            changes = "\n".join([f"{i+1}. {c}" for i, c in enumerate(sections["small_changes"])])
            parts.append(f"## 🌱 微小改变\n{changes}\n")
        
        # 7. 进步信号 + 专业支持
        if sections.get("progress_signals"):
            signals = "\n".join([f"- {s}" for s in sections["progress_signals"]])
            parts.append(f"## ✨ 进步信号\n接下来 1-2 周可以留意的积极信号：\n{signals}\n")
        
        if sections.get("professional_support"):
            parts.append(f"## 🤝 专业支持\n{sections['professional_support']}\n")
        
        return "\n".join(parts)
    
    def _get_fallback_result(self, input_data: Dict[str, Any]) -> HeartInterpretationOutput:
        """降级结果"""
        child_name = input_data.get("child_name", "孩子")
        
        fallback_text = f"""## 💖 我们觉得

亲爱的家长，谢谢您如此细致地观察{child_name}。

每一个行为都是孩子与世界沟通的方式，
而您正在学习如何更好地理解她。

## 🗺️ 发展地图

{child_name}正在发展重要的社会认知能力。
这需要时间、耐心和无数次的游戏体验。

## 🎯 优先解决的卡点

建议从最基础的能力开始，
就像搭积木一样，先站稳，再往上建。

## 💡 核心理念

帮助孩子"体验"而不是"理解"。

## 🎮 具体场景

- 场景 1：日常生活中自然创造体验机会
- 场景 2：游戏中温和引导发现

## 🌱 微小改变

1. 每天 1 次，留意孩子看向某物时的反应
2. 每周 1 次，玩简单的互动游戏
3. 每次孩子尝试时，关注过程而非结果

## ✨ 进步信号

接下来 1-2 周可以留意：
- 孩子不抗拒游戏
- 表现出好奇心
- 停留时间更长

## 🤝 专业支持

家庭游戏是发展的肥沃土壤。
如需更系统支持，可咨询作业治疗师或心理治疗师。
"""
        
        return HeartInterpretationOutput(
            emotional_anchor="亲爱的家长，谢谢您如此细致地观察孩子。",
            developmental_map="孩子正在发展重要的社会认知能力。",
            priority_explanation="建议从最基础的能力开始。",
            intervention_principle="帮助孩子'体验'而不是'理解'。",
            intervention_scenes=[
                "日常生活中自然创造体验机会",
                "游戏中温和引导发现",
            ],
            small_changes=[
                "每天 1 次，留意孩子看向某物时的反应",
                "每周 1 次，玩简单的互动游戏",
                "每次孩子尝试时，关注过程而非结果",
            ],
            progress_signals=[
                "孩子不抗拒游戏",
                "表现出好奇心",
                "停留时间更长",
            ],
            professional_support="家庭游戏是发展的肥沃土壤。如需更系统支持，可咨询作业治疗师或心理治疗师。",
            full_text=fallback_text,
        )
