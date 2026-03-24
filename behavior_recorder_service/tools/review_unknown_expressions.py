#!/usr/bin/env python3
"""
未知表达审查工具 V4.5.1

用途：
1. 查看高频未知表达
2. 将新表达添加到识别规则
3. 更新 intervention_patterns.json

使用方法：
python3 tools/review_unknown_expressions.py
"""

import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.unknown_expression_logger import get_unknown_logger


def main():
    logger = get_unknown_logger()
    report = logger.get_review_report()
    
    print("=" * 60)
    print("未知表达审查报告")
    print("=" * 60)
    print(f"总未知表达数：{report['total_unknown_expressions']}")
    print(f"需要审查的高频表达：{len(report['frequent_unknowns'])}")
    print()
    
    if not report['frequent_unknowns']:
        print("✅ 没有需要审查的高频未知表达")
        return
    
    print("高频未知表达列表：")
    print("-" * 60)
    
    for i, item in enumerate(report['frequent_unknowns'], 1):
        print(f"\n{i}. 表达：{item['expression']}")
        print(f"   出现次数：{item['count']}")
        print(f"   首次出现：{item['first_seen']}")
        print(f"   最近出现：{item['last_seen']}")
        print(f"   最近上下文：")
        for ctx in item['contexts']:
            print(f"     - Session: {ctx['session_id']}, Field: {ctx['field']}")
    
    print()
    print("-" * 60)
    print("操作建议：")
    print("1. 查看上述表达，判断属于哪种干预类型")
    print("2. 将新表达添加到 app/knowledge/intervention_patterns.json")
    print("3. 运行此脚本标记为已审查")
    print()
    
    # 交互式添加
    while True:
        choice = input("是否要添加新表达？(y/n): ").strip().lower()
        if choice != 'y':
            break
        
        expression = input("输入表达：").strip()
        category = input("属于哪类？(无外部干预/有外部干预/同伴反应): ").strip()
        
        # 添加到配置文件
        add_to_patterns(expression, category)
        
        # 标记为已审查
        logger.mark_reviewed(expression, category)
        print(f"✅ 已添加：{expression} → {category}")


def add_to_patterns(expression: str, category: str):
    """添加到 intervention_patterns.json"""
    patterns_path = Path("app/knowledge/intervention_patterns.json")
    
    with open(patterns_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 找到对应类别
    category_map = {
        "无外部干预": "no_intervention",
        "有外部干预": "active_intervention",
        "同伴反应": "peer_response",
    }
    
    category_key = category_map.get(category)
    if not category_key:
        print(f"❌ 未知类别：{category}")
        return
    
    # 添加到 exact_match 列表
    patterns = data["categories"][category_key]["patterns"]
    if expression not in patterns["exact_match"]:
        patterns["exact_match"].append(expression)
        print(f"✅ 已添加到 {category} 的精确匹配列表")
    
    # 保存
    with open(patterns_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
