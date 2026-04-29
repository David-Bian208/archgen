"""心伴解读 Agent 数据模型"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class DevelopmentalProfile(BaseModel):
    """发展画像"""
    strengths: List[str] = Field(default_factory=list, description="孩子已掌握的能力")
    current_focus: List[str] = Field(default_factory=list, description="当前发展焦点")
    potential_challenges: List[str] = Field(default_factory=list, description="潜在挑战")


class HypothesisRanking(BaseModel):
    """假设优先级"""
    id: str
    rank: int
    confidence: float
    description: str = ""


class HeartInterpretationInput(BaseModel):
    """心伴解读输入"""
    developmental_profile: DevelopmentalProfile
    attribution_statement: str  # 整合归因陈述
    hypotheses_ranking: List[HypothesisRanking]
    identified_problems: List[str]
    child_name: str = "孩子"
    child_age: str = "未明确"
    parent_concerns: List[str] = Field(default_factory=list, description="家长关注点")


class HeartInterpretationOutput(BaseModel):
    """心伴解读输出"""
    emotional_anchor: str = Field(..., description="情感锚点（共情开头）")
    developmental_map: str = Field(..., description="发展地图（问题→发展阶段）")
    priority_explanation: str = Field(..., description="优先级解释")
    intervention_principle: str = Field(..., description="核心理念（1 个）")
    intervention_scenes: List[str] = Field(default_factory=list, description="具体场景（2 个）")
    small_changes: List[str] = Field(default_factory=list, description="微小改变（3 个）")
    progress_signals: List[str] = Field(default_factory=list, description="进步信号")
    professional_support: str = Field(..., description="专业支持边界")
    full_text: str = Field(..., description="完整解读文本")
