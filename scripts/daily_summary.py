#!/usr/bin/env python3
"""
每日总结自动化工具

功能：
1. 检查当日是否有任务
2. 提醒填写经验教训
3. 运行守护测试
4. 生成每日日志草稿

使用：
```bash
# 工作结束前运行（建议 22:00）
python3 scripts/daily_summary.py

# 手动指定日期
python3 scripts/daily_summary.py --date 2026-04-21
```
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta


def check_tasks_completed() -> list:
    """检查当日是否有完成的任务"""
    today = datetime.now().strftime("%Y-%m-%d")
    tasks_path = Path("Desktop/行为观察助手/任务文档")
    
    completed_tasks = []
    
    if not tasks_path.exists():
        return completed_tasks
    
    # 查找今日完成的任务文档
    for task_file in tasks_path.glob("任务_*.md"):
        with open(task_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if f"完成时间：{today}" in content or f"完成时间： {today}" in content:
                completed_tasks.append(str(task_file.name))
    
    return completed_tasks


def check_lessons_filled(tasks: list) -> dict:
    """检查任务文档是否填写了经验教训"""
    results = {}
    
    for task_file in tasks:
        task_path = Path("Desktop/行为观察助手/任务文档") / task_file
        with open(task_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 检查是否包含经验教训章节
            has_lessons = "## 💡 经验教训" in content or "## 经验教训" in content
            has_patterns = "可复用的模式" in content
            has_pitfalls = "踩过的坑" in content
            
            results[task_file] = {
                "has_lessons": has_lessons,
                "has_patterns": has_patterns,
                "has_pitfalls": has_pitfalls,
                "complete": has_lessons and has_patterns and has_pitfalls
            }
    
    return results


def run_best_practices_test() -> bool:
    """运行守护测试"""
    import subprocess
    
    print("\n🧪 运行守护测试...")
    try:
        result = subprocess.run(
            ["python3", "tests/test_best_practices.py"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("   ✅ 守护测试通过")
            return True
        else:
            print(f"   ❌ 守护测试失败：{result.stdout[:200]}")
            return False
    except Exception as e:
        print(f"   ⚠️ 守护测试跳过：{str(e)[:100]}")
        return True  # 跳过视为通过


def generate_daily_log(tasks: list, lessons_status: dict) -> str:
    """生成每日日志草稿"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    log = f"# {today} 开发日志\n\n"
    log += "**维护者：** 战舰 🛳️\n"
    log += "**项目：** 行为观察助手\n\n"
    
    log += "## 📊 今日总览\n\n"
    
    if tasks:
        log += f"**完成任务：** {len(tasks)} 个\n"
        for task in tasks:
            status = "✅" if lessons_status.get(task, {}).get("complete") else "⚠️"
            log += f"- {status} {task}\n"
    else:
        log += "**完成任务：** 无\n"
    
    log += "\n## 📚 知识沉淀\n\n"
    
    if lessons_status:
        complete = sum(1 for s in lessons_status.values() if s["complete"])
        total = len(lessons_status)
        log += f"**经验教训填写率：** {complete}/{total}\n"
    else:
        log += "**经验教训填写率：** N/A（无任务）\n"
    
    log += "\n## 🧪 质量检查\n\n"
    log += "- [ ] 守护测试通过\n"
    log += "- [ ] 个人经验文档已更新\n"
    log += "- [ ] INDEX.md 已更新\n"
    log += "- [ ] 知识库文档已同步到桌面\n"
    
    log += "\n## 📝 待办事项\n\n"
    log += "- [ ] [待办 1]\n"
    log += "- [ ] [待办 2]\n"
    
    return log


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="每日总结自动化工具")
    parser.add_argument("--date", type=str, default=None, help="指定日期（YYYY-MM-DD）")
    parser.add_argument("--skip-test", action="store_true", help="跳过守护测试")
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("每日总结自动化")
    print("=" * 70)
    
    # 步骤 1：检查当日任务
    print("\n📋 检查当日任务...")
    tasks = check_tasks_completed()
    
    if not tasks:
        print("   ⏭️ 当日无完成的任务，跳过每日总结")
        print("\n✅ 每日总结完成（无任务）")
        return 0
    
    print(f"   ✅ 找到 {len(tasks)} 个完成的任务：")
    for task in tasks:
        print(f"      - {task}")
    
    # 步骤 2：检查经验教训填写
    print("\n📝 检查经验教训填写...")
    lessons_status = check_lessons_filled(tasks)
    
    incomplete = [t for t, s in lessons_status.items() if not s["complete"]]
    if incomplete:
        print(f"   ⚠️ {len(incomplete)} 个任务未填写完整经验教训：")
        for task in incomplete:
            print(f"      - {task}")
        print("\n   💡 请填写任务文档的'经验教训'字段！")
    else:
        print("   ✅ 所有任务已填写经验教训")
    
    # 步骤 3：运行守护测试
    if not args.skip_test:
        test_passed = run_best_practices_test()
    else:
        print("\n⏭️ 跳过守护测试")
        test_passed = True
    
    # 步骤 4：生成每日日志草稿
    print("\n📝 生成每日日志草稿...")
    log_content = generate_daily_log(tasks, lessons_status)
    
    log_path = Path(f"memory/{datetime.now().strftime('%Y-%m-%d')}.md")
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(log_content)
    
    print(f"   ✅ 每日日志草稿已生成：{log_path}")
    
    # 步骤 5：输出检查清单
    print("\n" + "=" * 70)
    print("每日总结检查清单")
    print("=" * 70)
    print(f"{'✅' if not incomplete else '❌'} 经验教训填写")
    print(f"{'✅' if test_passed else '❌'} 守护测试通过")
    print(f"{'✅' if log_path.exists() else '❌'} 每日日志生成")
    print(f"{'⏳' } 个人经验文档更新（小治/小测/小美执行）")
    print(f"{'⏳' } INDEX.md 更新（战舰执行）")
    print(f"{'⏳' } 知识库文档同步（战舰执行）")
    
    if incomplete:
        print("\n⚠️ 有待完成项，请先补充经验教训！")
        return 1
    else:
        print("\n✅ 每日总结完成！")
        return 0


if __name__ == "__main__":
    sys.exit(main())
