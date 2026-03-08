"""
专业知识库模块
提供行为鉴别诊断的结构化知识
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class BehaviorKnowledgeBase:
    """行为鉴别知识库"""

    def __init__(self):
        """初始化知识库"""
        self.knowledge_path = Path(__file__).parent / "behavior_hypotheses.json"
        self.data = {}
        self.load()

    def load(self) -> None:
        """加载知识库"""
        if not self.knowledge_path.exists():
            logger.warning(f"知识库文件不存在：{self.knowledge_path}")
            return

        try:
            with open(self.knowledge_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            logger.info(f"知识库加载成功：{len(self.data.get('scenarios', []))} 个场景")
        except Exception as e:
            logger.error(f"知识库加载失败：{e}")

    def match_scenario(self, keywords: list[str]) -> Optional[dict]:
        """
        根据关键词匹配最相关的场景（V3.4 - 支持 6 个场景）

        Args:
            keywords: 行为关键词列表（如 ["发呆", "走神", "不做"]）

        Returns:
            匹配的场景字典，未匹配则返回 None
        """
        # 优先级匹配：更具体的行为关键词优先
        matched_scenarios = []

        for scenario in self.data.get("scenarios", []):
            scene_keywords = scenario.get("keywords", [])
            match_count = 0
            matched_kw = []

            for kw in keywords:
                if kw in scene_keywords:
                    match_count += 1
                    matched_kw.append(kw)

            if match_count > 0:
                matched_scenarios.append({
                    "scenario": scenario,
                    "match_count": match_count,
                    "matched_keywords": matched_kw,
                })

        # 按匹配数量排序，返回匹配度最高的
        if matched_scenarios:
            matched_scenarios.sort(key=lambda x: x["match_count"], reverse=True)
            best_match = matched_scenarios[0]
            logger.info(f"场景匹配成功：{best_match['scenario'].get('scene_key')} (关键词：{best_match['matched_keywords']}, 匹配数：{best_match['match_count']})")
            return best_match["scenario"]

        logger.info(f"未匹配到场景，关键词：{keywords}")
        return None

    def get_competing_hypotheses(self, scene_key: str) -> list[dict]:
        """
        获取指定场景的竞争性假设列表

        Args:
            scene_key: 场景键（如 "task_disengagement"）

        Returns:
            竞争性假设列表
        """
        for scenario in self.data.get("scenarios", []):
            if scenario.get("scene_key") == scene_key:
                return scenario.get("competing_hypotheses", [])

        return []

    def generate_discriminating_question(self, hypotheses: list[dict]) -> str:
        """
        基于竞争性假设生成鉴别性问题

        Args:
            hypotheses: 竞争性假设列表

        Returns:
            综合性的鉴别性问题
        """
        if not hypotheses:
            return "能再详细描述一下当时的情况吗？"

        # 提取各假设的关键鉴别问题
        questions = []
        for h in hypotheses:
            q = h.get("key_discriminating_question", "")
            if q:
                questions.append(q)

        # 融合为综合性问题
        if len(questions) >= 2:
            return f"为了更好地理解孩子行为的性质，可以再描述一个细节吗？{questions[0]} 另外，{questions[1].split('？')[0] if '？' in questions[1] else questions[1]}？"
        elif questions:
            return questions[0]
        else:
            return "能再详细描述一下当时的情况吗？"


# 全局知识库实例
_knowledge_base: Optional[BehaviorKnowledgeBase] = None


def get_knowledge_base() -> BehaviorKnowledgeBase:
    """获取全局知识库实例"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = BehaviorKnowledgeBase()
    return _knowledge_base
