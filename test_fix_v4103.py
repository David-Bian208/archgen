#!/usr/bin/env python3
"""
V4.10.3 编号层级修复 - 单元测试
直接测试 _fix_capability_gap_format 方法
"""

import sys
import re
sys.path.insert(0, '/home/admin/.openclaw/workspace/behavior_recorder_service')

from app.agents.insight_analyzer import InsightAnalyzer
from app.llm.base import LLMClient

def test_fix_no_bold():
    """测试无加粗格式的修复"""
    
    print("=" * 60)
    print("V4.10.3 编号层级修复测试 - 无加粗格式")
    print("=" * 60)
    
    # 模拟 LLM 返回的错误格式（三个标题都用"1."，且无加粗）
    test_input = {
        "clinical_differential": """1. 鉴别与排除：
   1. 为何不是'提示依赖'：行为是自发、主动的
   2. 为何不是'社交技能不足'：行为发生在成人 - 儿童互动场景

2. 核心假设：计划改变引发的认知 - 情绪僵化

3. 能力缺口分析：
   1. 认知灵活性不足：'说不是这样的'→表明难以快速更新认知脚本
   2. 情绪调节困难：'哭，不肯下车'→表明难以有效管理情绪强度
"""
    }
    
    print("\n📥 输入（错误格式）:")
    print(test_input["clinical_differential"])
    
    # 创建分析器实例（不需要真实的 LLM 客户端）
    class MockLLM:
        def generate_json(self, **kwargs):
            return {}
    
    analyzer = InsightAnalyzer(MockLLM())
    
    # 执行修复
    result = analyzer._fix_capability_gap_format(test_input)
    
    print("\n📤 输出（修复后）:")
    print(result["clinical_differential"])
    
    # 验证修复结果
    print("\n🔍 验证修复结果:")
    
    output = result["clinical_differential"]
    
    # 检查主标题编号
    lines = output.split('\n')
    # 匹配：可选空格 + 数字 + . + 空格 + 标题（包含鉴别与排除/核心假设/能力缺口分析）+ 冒号
    title_keywords = ["鉴别与排除", "核心假设", "能力缺口分析"]
    title_lines = []
    for l in lines:
        stripped = l.strip()
        if any(re.match(r'^\d+\.\s*' + kw, stripped) for kw in title_keywords):
            title_lines.append(l)
    
    print(f"  主标题行数：{len(title_lines)}")
    for tl in title_lines:
        print(f"    - {tl.strip()[:60]}")
    
    # 检查是否有序列号 1. 2. 3.
    has_1 = any(l.strip().startswith('1.') for l in title_lines)
    has_2 = any(l.strip().startswith('2.') for l in title_lines)
    has_3 = any(l.strip().startswith('3.') for l in title_lines)
    
    print(f"  有 1. 标题：{'✅' if has_1 else '❌'}")
    print(f"  有 2. 标题：{'✅' if has_2 else '❌'}")
    print(f"  有 3. 标题：{'✅' if has_3 else '❌'}")
    
    # 检查能力缺口分析子项是否用 •
    if "能力缺口分析" in output:
        gap_section = output.split("能力缺口分析")[1]
        has_bullet = '•' in gap_section
        has_numbered = any(l.strip().startswith(('1.', '2.', '3.')) for l in gap_section.split('\n') if l.strip() and ':' in l)
        
        print(f"  子项用 • 符号：{'✅' if has_bullet else '❌'}")
        print(f"  子项无编号：{'✅' if not has_numbered else '❌'}")
    
    # 最终判断
    success = has_1 and has_2 and has_3
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试通过：编号层级修复正确")
    else:
        print("❌ 测试失败：编号层级修复不正确")
    print("=" * 60)
    
    return success

def test_fix_with_bold():
    """测试有加粗格式的修复"""
    
    print("\n\n" + "=" * 60)
    print("V4.10.3 编号层级修复测试 - 有加粗格式")
    print("=" * 60)
    
    # 模拟 LLM 返回的错误格式（三个标题都用"1."，且有加粗）
    test_input = {
        "clinical_differential": """1. **鉴别与排除**：
   1. **为何不是'提示依赖'**：行为是自发、主动的
   2. **为何不是'社交技能不足'**：行为发生在成人 - 儿童互动场景

2. **核心假设**：计划改变引发的认知 - 情绪僵化

3. **能力缺口分析**：
   1. **认知灵活性不足**：'说不是这样的'→表明难以快速更新认知脚本
   2. **情绪调节困难**：'哭，不肯下车'→表明难以有效管理情绪强度
"""
    }
    
    print("\n📥 输入（错误格式）:")
    print(test_input["clinical_differential"])
    
    # 创建分析器实例
    class MockLLM:
        def generate_json(self, **kwargs):
            return {}
    
    analyzer = InsightAnalyzer(MockLLM())
    
    # 执行修复
    result = analyzer._fix_capability_gap_format(test_input)
    
    print("\n📤 输出（修复后）:")
    print(result["clinical_differential"])
    
    # 验证修复结果
    output = result["clinical_differential"]
    
    # 检查主标题编号
    lines = output.split('\n')
    title_lines = [l for l in lines if l.strip().startswith(('1.', '2.', '3.')) and '**' in l]
    
    print(f"\n 验证修复结果:")
    print(f"  主标题行数：{len(title_lines)}")
    
    has_1 = any(l.strip().startswith('1.') for l in title_lines)
    has_2 = any(l.strip().startswith('2.') for l in title_lines)
    has_3 = any(l.strip().startswith('3.') for l in title_lines)
    
    print(f"  有 1. 标题：{'✅' if has_1 else '❌'}")
    print(f"  有 2. 标题：{'✅' if has_2 else '❌'}")
    print(f"  有 3. 标题：{'✅' if has_3 else '❌'}")
    
    # 检查能力缺口分析子项是否用 •
    if "能力缺口分析" in output:
        gap_section = output.split("能力缺口分析")[1]
        has_bullet = '•' in gap_section
        
        print(f"  子项用 • 符号：{'✅' if has_bullet else '❌'}")
    
    # 最终判断
    success = has_1 and has_2 and has_3
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试通过：编号层级修复正确")
    else:
        print("❌ 测试失败：编号层级修复不正确")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    try:
        result1 = test_fix_no_bold()
        result2 = test_fix_with_bold()
        
        print("\n\n" + "=" * 60)
        print("总体结果:")
        print(f"  无加粗格式测试：{'✅ 通过' if result1 else '❌ 失败'}")
        print(f"  有加粗格式测试：{'✅ 通过' if result2 else ' 失败'}")
        print("=" * 60)
        
        if result1 and result2:
            print("\n✅ 所有测试通过！")
            sys.exit(0)
        else:
            print("\n❌ 有测试失败！")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
