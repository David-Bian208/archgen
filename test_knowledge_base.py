#!/usr/bin/env python
"""知识库模块测试"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.knowledge_base import KnowledgeBaseReader

def test_knowledge_base():
    """测试知识库读取模块"""
    config = {
        "root_path": str(Path(__file__).parent / "knowledge_base"),
        "mode": "local",
    }
    reader = KnowledgeBaseReader(config)

    print("=== 测试 1: 列出分类 ===")
    categories = reader.list_categories()
    for cat in categories:
        print(f"  - {cat['key']}: {cat['name']} ({cat['file_count']} 文件)")

    print("\n=== 测试 2: 列出 business 目录 ===")
    files = reader.list_directory("business")
    for f in files:
        print(f"  - {f['name']} ({f['size']} bytes)")

    print("\n=== 测试 3: 读取文件 ===")
    content = reader.read_file("business/swot_example.md")
    if content:
        print(f"  内容预览: {content[:50]}...")
    else:
        print("  读取失败!")

    print("\n=== 测试 4: 获取文件信息 ===")
    info = reader.get_file_info("product/user_journey.md")
    if info:
        print(f"  文件名: {info['name']}")
        print(f"  大小: {info['size']} bytes")
        print(f"  内容: {info['content'][:50]}...")
    else:
        print("  获取失败!")

    print("\n=== 测试 5: 读取不存在的文件 ===")
    content = reader.read_file("nonexistent.md")
    print(f"  结果: {content}")

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_knowledge_base()
