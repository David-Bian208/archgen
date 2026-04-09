#!/usr/bin/env python3
"""
四维度归因执行器

用法：
    命令行：python3 executor.py "行为描述"
    Python API：from executor import FourDimensionAnalyzer
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any

# 添加项目路径，复用主项目的 LLM 客户端
PROJECT_ROOT = Path('/home/admin/.openclaw/workspace/behavior_recorder_service')
sys.path.insert(0, str(PROJECT_ROOT))

# 导入提示词模板
from prompt import FOUR_DIMENSION_PROMPT, FOUR_DIMENSION_PROMPT_SHORT

# 导入 LLM 客户端
try:
    from app.llm.openai_client import OpenAIClient
except ImportError:
    print("❌ 无法导入 LLM 客户端（OpenAIClient）")
    print("请确认 behavior_recorder_service/app/llm/openai_client.py 存在")
    sys.exit(1)


class FourDimensionAnalyzer:
    """四维度归因分析器"""
    
    def __init__(self, short_mode: bool = False):
        self.short_mode = short_mode
        self.prompt_template = FOUR_DIMENSION_PROMPT_SHORT if short_mode else FOUR_DIMENSION_PROMPT
        self.client = OpenAIClient(
            api_key=os.getenv('LLM_API_KEY', ''),
            base_url=os.getenv('LLM_BASE_URL', 'https://api.deepseek.com'),
            model=os.getenv('LLM_MODEL', 'deepseek-chat')
        )
    
    def analyze(self, behavior_description: str) -> Dict[str, Any]:
        """从四维度分析行为"""
        try:
            prompt = self.prompt_template.format(behavior=behavior_description)
            response = self.client.generate(
                system_prompt="你是一位认知神经科学家，擅长从多维度分析儿童行为。",
                user_prompt=prompt,
                max_tokens=1500
            )
            return self._parse_response(response, behavior_description)
        except Exception as e:
            return {
                "success": False,
                "attribution": "",
                "dimensions": {},
                "summary": "",
                "input": behavior_description,
                "error": str(e)
            }
    
    def _parse_response(self, response: str, behavior: str) -> Dict[str, Any]:
        """解析 LLM 响应"""
        dimensions = {
            "theory_of_mind": self._extract_section(response, "心理理论"),
            "executive_function": self._extract_section(response, "执行功能"),
            "visual_spatial": self._extract_section(response, "视觉"),
            "language": self._extract_section(response, "语言")
        }
        return {
            "success": True,
            "attribution": response,
            "dimensions": dimensions,
            "summary": self._extract_summary(response),
            "input": behavior
        }
    
    def _extract_section(self, text: str, section_name: str) -> str:
        """提取指定维度内容"""
        start = text.find(f"**{section_name}")
        if start == -1:
            return ""
        end_markers = ["**总结", "**语言", "```"]
        end = len(text)
        for marker in end_markers:
            pos = text.find(marker, start + 10)
            if pos != -1 and pos < end:
                end = pos
        return text[start:end].strip()
    
    def _extract_summary(self, text: str) -> str:
        """提取总结部分"""
        start = text.find("**总结**")
        if start == -1:
            return ""
        return text[start:].strip()


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("📖 用法：python3 executor.py \"行为描述\"")
        print("选项：--short 使用简短模式（300 字以内）")
        sys.exit(1)
    
    short_mode = "--short" in sys.argv
    behavior = sys.argv[1]
    
    if behavior.startswith("--"):
        print("❌ 错误：行为描述不能作为第一个参数")
        sys.exit(1)
    
    print(f"🔍 分析行为：{behavior}")
    print("=" * 60)
    
    analyzer = FourDimensionAnalyzer(short_mode=short_mode)
    result = analyzer.analyze(behavior)
    
    if result["success"]:
        print(result["attribution"])
        print("=" * 60)
        print(f"✅ 分析完成")
        print("\n📊 维度覆盖:")
        for dim_name, dim_content in result["dimensions"].items():
            status = "✅" if dim_content else "❌"
            print(f"  {status} {dim_name}")
    else:
        print(f"❌ 分析失败：{result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
