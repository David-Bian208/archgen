"""
临床规则注册表 (Clinical Rules Registry)

灵感来源：claw-code 项目的 tools.py / execution_registry.py
用途：将临床规则从硬编码改为可配置、可测试、可审计的注册表模式

核心设计：
1. 规则与执行逻辑分离
2. 统一的规则数据结构
3. 支持规则覆盖率审计
4. 便于新增临床知识

使用方式：
    from app.knowledge.clinical_rules_registry import ClinicalRulesRegistry
    
    registry = ClinicalRulesRegistry()
    matches = registry.evaluate(observation)
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class RuleCategory(str, Enum):
    """规则类别"""
    SAFETY = "safety"              # 安全优先
    SOCIAL = "social"              # 社交功能
    RIGIDITY = "rigidity"          # 坚持同一性
    SENSORY = "sensory"            # 感觉寻求
    AVOIDANCE = "avoidance"        # 逃避需求
    ATTENTION = "attention"        # 寻求关注
    PROMPT_DEPENDENT = "prompt_dependent"  # 提示依赖


@dataclass(frozen=True)
class ClinicalRule:
    """
    临床规则
    
    Attributes:
        id: 规则唯一标识
        name: 规则名称
        category: 规则类别
        condition_keywords: 触发关键词列表
        condition_context: 触发上下文要求
        hypothesis: 对应的临床假设
        confidence: 默认置信度
        description: 规则描述
        references: 参考依据
    """
    id: str
    name: str
    category: RuleCategory
    condition_keywords: List[str]
    condition_context: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None  # 排除关键词（避免误报）
    hypothesis: str = ""
    confidence: float = 0.8
    description: str = ""
    references: List[str] = field(default_factory=list)
    
    def matches(self, text: str) -> bool:
        """
        检查文本是否匹配此规则
        
        Args:
            text: 待检查的文本（行为描述 + 情境）
            
        Returns:
            bool: 是否匹配
        """
        text_lower = text.lower()
        
        # 检查排除关键词（优先）
        if self.exclude_keywords:
            for exclude in self.exclude_keywords:
                if exclude.lower() in text_lower:
                    return False
        
        # 检查触发关键词
        has_keyword = any(kw.lower() in text_lower for kw in self.condition_keywords)
        if not has_keyword:
            return False
        
        # 检查上下文要求（如果有）
        if self.condition_context:
            has_context = any(ctx.lower() in text_lower for ctx in self.condition_context)
            if not has_context:
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "condition_keywords": self.condition_keywords,
            "condition_context": self.condition_context,
            "exclude_keywords": self.exclude_keywords,
            "hypothesis": self.hypothesis,
            "confidence": self.confidence,
            "description": self.description,
            "references": self.references,
        }


@dataclass(frozen=True)
class RuleMatch:
    """规则匹配结果"""
    rule: ClinicalRule
    matched_text: str
    confidence: float
    evidence: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "rule_id": self.rule.id,
            "rule_name": self.rule.name,
            "category": self.rule.category.value,
            "hypothesis": self.rule.hypothesis,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


class ClinicalRulesRegistry:
    """
    临床规则注册表
    
    管理所有临床规则，支持：
    - 规则注册
    - 规则匹配
    - 规则查询
    - 覆盖率统计
    """
    
    def __init__(self):
        """初始化注册表"""
        self._rules: Dict[str, ClinicalRule] = {}
        self._load_default_rules()
        logger.info(f"ClinicalRulesRegistry 初始化完成，加载 {len(self._rules)} 条规则")
    
    def _load_default_rules(self) -> None:
        """加载默认临床规则"""
        
        # ========== 安全优先规则 ==========
        self.register(ClinicalRule(
            id="SAFETY-001",
            name="危险行为检测",
            category=RuleCategory.SAFETY,
            condition_keywords=["爬高", "危险", "利器", "冲撞", "跑到马路", "触电", "溺水", "水池"],
            hypothesis="安全风险优先处理",
            confidence=1.0,
            description="涉及人身安全的行为必须优先处理",
            references=["V4.5.21 P0 Fix"],
        ))
        
        self.register(ClinicalRule(
            id="SAFETY-002",
            name="火源危险检测",
            category=RuleCategory.SAFETY,
            condition_keywords=["火"],
            condition_context=["玩火", "点火", "烧", "火灾", "打火机", "火柴"],
            exclude_keywords=["发火", "生气", "脾气"],  # 排除"发脾气"误报
            hypothesis="安全风险优先处理",
            confidence=1.0,
            description="涉及火源的行为需要上下文确认",
            references=["V4.5.21 P0 Fix"],
        ))
        
        # ========== 社交功能规则 ==========
        self.register(ClinicalRule(
            id="SOCIAL-001",
            name="社交信号忽略",
            category=RuleCategory.SOCIAL,
            condition_keywords=["不看", "不理", "忽略", "没反应", "叫不应"],
            hypothesis="社交认知能力还在发展中",
            confidence=0.85,
            description="孩子可能还没学会监测他人反应",
            references=["V4.10.2"],
        ))
        
        self.register(ClinicalRule(
            id="SOCIAL-002",
            name="共同注意困难",
            category=RuleCategory.SOCIAL,
            condition_keywords=["不看", "不指", "不分享", "各玩各"],
            hypothesis="共同注意能力还在发展中",
            confidence=0.8,
            description="孩子可能还没学会与他人分享注意力",
            references=["V4.10.2"],
        ))
        
        self.register(ClinicalRule(
            id="SOCIAL-003",
            name="社交发起困难",
            category=RuleCategory.SOCIAL,
            condition_keywords=["不说话", "不主动", "等待", "被动"],
            hypothesis="社交发起能力还在发展中",
            confidence=0.8,
            description="孩子可能还没学会主动发起社交",
            references=["V4.10.2"],
        ))
        
        # ========== 坚持同一性规则 ==========
        self.register(ClinicalRule(
            id="RIGIDITY-001",
            name="规则坚持",
            category=RuleCategory.RIGIDITY,
            condition_keywords=["必须", "一定", "总是", "不肯", "拒绝改变"],
            hypothesis="坚持同一性需求",
            confidence=0.85,
            description="孩子对环境一致性有较高需求",
            references=["V4.5.21"],
        ))
        
        self.register(ClinicalRule(
            id="RIGIDITY-002",
            name="程序坚持",
            category=RuleCategory.RIGIDITY,
            condition_keywords=["顺序", "流程", "步骤", "固定"],
            hypothesis="坚持同一性需求",
            confidence=0.8,
            description="孩子对程序一致性有较高需求",
            references=["V4.5.21"],
        ))
        
        # ========== 感觉寻求规则 ==========
        self.register(ClinicalRule(
            id="SENSORY-001",
            name="视觉刺激寻求",
            category=RuleCategory.SENSORY,
            condition_keywords=["看", "盯着", "转", "闪烁", "灯光"],
            hypothesis="感觉寻求功能",
            confidence=0.75,
            description="行为可能是为了获得视觉刺激",
            references=["V4.5.21"],
        ))
        
        self.register(ClinicalRule(
            id="SENSORY-002",
            name="触觉刺激寻求",
            category=RuleCategory.SENSORY,
            condition_keywords=["摸", "碰", "蹭", "触感", "材质"],
            hypothesis="感觉寻求功能",
            confidence=0.75,
            description="行为可能是为了获得触觉刺激",
            references=["V4.5.21"],
        ))
        
        # ========== 逃避需求规则 ==========
        self.register(ClinicalRule(
            id="AVOIDANCE-001",
            name="任务逃避",
            category=RuleCategory.AVOIDANCE,
            condition_keywords=["不做", "逃跑", "离开", "拒绝", "不要"],
            condition_context=["任务", "要求", "学习", "练习"],
            hypothesis="逃避需求功能",
            confidence=0.8,
            description="行为可能是为了逃避困难任务",
            references=["V4.5.21"],
        ))
        
        self.register(ClinicalRule(
            id="AVOIDANCE-002",
            name="社交逃避",
            category=RuleCategory.AVOIDANCE,
            condition_keywords=["躲", "藏", "离开", "不参与"],
            condition_context=["社交", "游戏", "互动", "群体"],
            hypothesis="逃避需求功能",
            confidence=0.75,
            description="行为可能是为了逃避社交压力",
            references=["V4.5.21"],
        ))
        
        # ========== 寻求关注规则 ==========
        self.register(ClinicalRule(
            id="ATTENTION-001",
            name="关注寻求",
            category=RuleCategory.ATTENTION,
            condition_keywords=["看", "注意", "叫", "吸引", "表现"],
            condition_context=["大人", "老师", "家长", "他人"],
            hypothesis="寻求关注功能",
            confidence=0.8,
            description="行为可能是为了获得他人关注",
            references=["V4.5.21"],
        ))
        
        # ========== 提示依赖规则 ==========
        self.register(ClinicalRule(
            id="PROMPT-001",
            name="视觉提示依赖",
            category=RuleCategory.PROMPT_DEPENDENT,
            condition_keywords=["提示", "提醒", "指", "看", "视觉"],
            hypothesis="提示依赖功能",
            confidence=0.8,
            description="孩子需要视觉提示才能完成任务",
            references=["V4.3 Hotfix"],
        ))
        
        self.register(ClinicalRule(
            id="PROMPT-002",
            name="动作提示依赖",
            category=RuleCategory.PROMPT_DEPENDENT,
            condition_keywords=["示范", "手把手", "辅助", "帮助"],
            hypothesis="提示依赖功能",
            confidence=0.8,
            description="孩子需要动作提示才能完成任务",
            references=["V4.3 Hotfix"],
        ))
    
    def register(self, rule: ClinicalRule) -> None:
        """
        注册规则
        
        Args:
            rule: 临床规则
        """
        self._rules[rule.id] = rule
        logger.debug(f"注册规则：{rule.id} - {rule.name}")
    
    def get(self, rule_id: str) -> Optional[ClinicalRule]:
        """
        获取规则
        
        Args:
            rule_id: 规则 ID
            
        Returns:
            ClinicalRule or None
        """
        return self._rules.get(rule_id)
    
    def list_all(self) -> List[ClinicalRule]:
        """列出所有规则"""
        return list(self._rules.values())
    
    def list_by_category(self, category: RuleCategory) -> List[ClinicalRule]:
        """按类别列出规则"""
        return [r for r in self._rules.values() if r.category == category]
    
    def evaluate(self, text: str, min_confidence: float = 0.5) -> List[RuleMatch]:
        """
        评估文本，返回匹配的规则
        
        Args:
            text: 待评估的文本（行为描述 + 情境）
            min_confidence: 最低置信度阈值
            
        Returns:
            List[RuleMatch]: 匹配的规则列表，按置信度排序
        """
        matches = []
        
        for rule in self._rules.values():
            if rule.matches(text):
                match = RuleMatch(
                    rule=rule,
                    matched_text=text[:100],  # 截断避免过长
                    confidence=rule.confidence,
                    evidence=f"匹配关键词：{', '.join(rule.condition_keywords[:3])}",
                )
                if match.confidence >= min_confidence:
                    matches.append(match)
        
        # 按置信度排序
        matches.sort(key=lambda m: -m.confidence)
        
        logger.info(f"规则评估：{len(matches)} 条匹配（文本：{text[:50]}...）")
        return matches
    
    def count(self) -> int:
        """获取规则总数"""
        return len(self._rules)
    
    def count_by_category(self) -> Dict[str, int]:
        """按类别统计规则数量"""
        counts = {}
        for rule in self._rules.values():
            cat = rule.category.value
            counts[cat] = counts.get(cat, 0) + 1
        return counts
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_rules": len(self._rules),
            "by_category": self.count_by_category(),
            "rule_ids": list(self._rules.keys()),
        }


# ========== 全局单例 ==========

_registry_instance: Optional[ClinicalRulesRegistry] = None


def get_clinical_rules_registry() -> ClinicalRulesRegistry:
    """获取全局注册表实例"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ClinicalRulesRegistry()
    return _registry_instance


# ========== CLI 入口 ==========

if __name__ == "__main__":
    registry = get_clinical_rules_registry()
    
    print("📊 临床规则注册表统计")
    print("=" * 50)
    stats = registry.get_statistics()
    print(f"规则总数：{stats['total_rules']}")
    print(f"按类别分布：{stats['by_category']}")
    print()
    
    # 测试匹配
    test_cases = [
        "小明看到打火机想拿起来玩火",
        "小明不看老师，叫也不理",
        "小明必须按固定顺序摆放玩具",
        "小明盯着旋转的风扇看",
        "小明不做作业，逃跑",
    ]
    
    print("🧪 测试匹配")
    print("=" * 50)
    for test in test_cases:
        print(f"\n测试文本：{test}")
        matches = registry.evaluate(test)
        for match in matches[:3]:  # 显示 top 3
            print(f"  - {match.rule.name} (置信度：{match.confidence})")
