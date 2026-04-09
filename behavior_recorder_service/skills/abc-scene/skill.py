#!/usr/bin/env python3
"""
ABC 场景描述提取 Skill

从家长自然语言描述中提取结构化的 ABC 信息：
- Antecedent（前因/情境）
- Behavior（行为）
- Consequence（后果/回应）
- Child Age（孩子年龄）

输入示例：
"老师好，OK 玩薯片盒子游戏...问她'妈妈会看到什么'，她说'糖'..."

输出格式：
{
  "antecedent": "...",
  "behavior": "...",
  "consequence": "...",
  "child_age": "..."
}
"""

import re
import json
from typing import Dict, Optional


class ABCSceneExtractor:
    """ABC 场景提取器"""
    
    def __init__(self):
        # 年龄提取模式
        self.age_patterns = [
            r'(\d+) 岁',  # 5 岁
            r'(\d+) 周岁',  # 5 周岁
        ]
        
        # 孩子名称提取模式
        self.child_name_patterns = [
            r'(OK|玥玥|小明|小红|宝宝|孩子|小朋友)',
        ]
    
    def extract(self, text: str) -> Dict:
        """
        从文本中提取 ABC 信息
        
        Args:
            text: 家长的自然语言描述
            
        Returns:
            包含 antecedent, behavior, consequence, child_age 的字典
        """
        # 1. 提取孩子年龄
        child_age = self._extract_age(text)
        
        # 2. 提取孩子名称
        child_name = self._extract_child_name(text)
        
        # 3. 提取 ABC 信息
        antecedent = self._extract_antecedent(text, child_name)
        behavior = self._extract_behavior(text, child_name)
        consequence = self._extract_consequence(text, child_name)
        
        return {
            "antecedent": antecedent or "未明确",
            "behavior": behavior or "未明确",
            "consequence": consequence or "未明确",
            "child_age": child_age or "未明确",
            "child_name": child_name or "孩子"
        }
    
    def _extract_age(self, text: str) -> Optional[str]:
        """提取孩子年龄"""
        # 先尝试提取岁 + 月
        age_match = re.search(r'(\d+) 岁 (\d+) 个月', text)
        if age_match:
            return f"{age_match.group(1)}岁{age_match.group(2)}个月"
        
        # 提取岁
        for pattern in self.age_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"{match.group(1)}岁"
        
        return None
    
    def _extract_child_name(self, text: str) -> Optional[str]:
        """提取孩子名称"""
        for pattern in self.child_name_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None
    
    def _extract_antecedent(self, text: str, child_name: str) -> Optional[str]:
        """
        提取前因/情境
        关键词：玩...游戏、当...时、在...情况下、老师问、妈妈问
        """
        # 模式 1：玩...游戏（直接匹配）
        match = re.search(r'玩.*游戏', text)
        if match:
            content = match.group(0)
            if '在' in content:
                return f"{child_name or '孩子'}{content}"
            else:
                return f"{child_name or '孩子'}在{content}"
        
        # 模式 2：游戏场景（孩子名 + 玩）
        match = re.search(rf'{child_name or "孩子"}.*?玩.*?(?:，|。|,)', text)
        if match:
            return f"{child_name or '孩子'}{match.group(0).rstrip('，。, ')}"
        
        # 模式 3：提问场景
        match = re.search(r'(?:问 | 询问)(.+?)(?:说 | 回答 | 回应)', text, re.IGNORECASE)
        if match:
            return f"大人问{match.group(1)}"
        
        # 模式 4：时间状语
        match = re.search(r'(?:当 | 在)(.+?)(?:时 | 的时候 | ，|，)', text)
        if match:
            return f"当{match.group(1)}时"
        
        return None
    
    def _extract_behavior(self, text: str, child_name: str) -> Optional[str]:
        """
        提取行为
        关键词：她说、他做、孩子说、回答说
        """
        # 模式 1：直接引语（她说'...'）- 先尝试
        match = re.search(rf'(?:她 | 他 |{child_name or "孩子"}).*?说.*?[\'"](.+?)[\'"]', text)
        if match:
            return f"{child_name or '孩子'}说：'{match.group(1)}'"
        
        # 模式 2：间接引语（她说...）
        match = re.search(rf'(?:她 | 他 |{child_name or "孩子"}) 说 (.+?)(?:，|。|！|？)', text)
        if match:
            return f"{child_name or '孩子'}说{match.group(1)}"
        
        # 模式 3：行为描述
        match = re.search(rf'{child_name or "孩子"}(.+?)(?:，|。|！|？)', text)
        if match:
            return f"{child_name or '孩子'}{match.group(1)}"
        
        return None
    
    def _extract_consequence(self, text: str, child_name: str) -> Optional[str]:
        """
        提取后果/回应
        关键词：老师说、妈妈说、然后、之后、于是
        """
        # 模式 1：大人回应
        match = re.search(r'(?:老师 | 妈妈 | 爸爸 | 大人)(.+?)(?:说 | 做 | 回应)', text)
        if match:
            return f"大人{match.group(1)}"
        
        # 模式 2：后续事件
        match = re.search(r'(?:然后 | 之后 | 于是 | 接着)(.+?)(?:，|。|！|？)', text)
        if match:
            return match.group(1)
        
        return None


def extract_abc_scene(text: str) -> Dict:
    """
    便捷函数：从文本中提取 ABC 场景
    
    Args:
        text: 家长的自然语言描述
        
    Returns:
        包含 antecedent, behavior, consequence, child_age 的字典
    """
    extractor = ABCSceneExtractor()
    return extractor.extract(text)


# 命令行入口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法：python3 skill.py \"家长描述文本\"")
        print("示例：")
        print('python3 skill.py "老师好，OK 玩薯片盒子游戏...问她\'妈妈会看到什么\'，她说\'糖\'..."')
        sys.exit(1)
    
    text = sys.argv[1]
    result = extract_abc_scene(text)
    print("=" * 60)
    print("ABC 场景提取结果")
    print("=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=" * 60)
