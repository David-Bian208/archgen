#!/usr/bin/env python3
"""
从日志提取完整对话流程
生成每个案例的详细对话记录
"""

import re
import json
from datetime import datetime
from pathlib import Path

LOG_FILE = "/home/admin/.openclaw/workspace/behavior_recorder_service/server.log"
OUTPUT_DIR = Path("/home/admin/Desktop/10 案例质量测试")

# 10 个测试案例
TEST_CASES = [
    {"id": 1, "name": "典型提示依赖", "input": "孩子 5 岁，在幼儿园做操时，不看老师就不会做，一看老师就会做。", "expected": "提示依赖"},
    {"id": 2, "name": "逃避难度", "input": "我家孩子 7 岁，一写数学作业就说太难了，然后开始哭。", "expected": "逃避难度"},
    {"id": 3, "name": "感觉逃避", "input": "一到超市他就捂耳朵，哭闹要出去。", "expected": "感觉逃避"},
    {"id": 4, "name": "寻求关注", "input": "我打电话时，他就故意大声唱歌或捣乱。", "expected": "寻求关注"},
    {"id": 5, "name": "自我刺激", "input": "他总是不停地晃手，盯着手看，叫名字没反应。", "expected": "自动强化"},
    {"id": 6, "name": "拒绝穿衣", "input": "早上不肯穿衣服，挑衣服。", "expected": "过渡困难"},
    {"id": 7, "name": "不会轮流", "input": "游戏时不会等，总是抢着来。", "expected": "社交技能缺陷"},
    {"id": 8, "name": "眼神回避", "input": "说话时不看人，低头或看别处。", "expected": "社交注意缺陷"},
    {"id": 9, "name": "完美主义", "input": "写字擦来擦去，纸都破了。", "expected": "焦虑/僵化思维"},
    {"id": 10, "name": "挑食", "input": "只吃白色食物，米饭、面条、馒头。", "expected": "感觉敏感"},
]

def extract_conversations():
    """从日志提取对话"""
    conversations = {}
    current_session = None
    
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            # 提取会话创建
            if '创建新会话' in line:
                match = re.search(r'创建新会话：([a-f0-9]+)', line)
                if match:
                    current_session = match.group(1)
                    conversations[current_session] = []
            
            # 提取用户输入
            if '收到对话' in line and 'input=' in line:
                match = re.search(r'input=(.+?)\.\.\.', line)
                if match and current_session:
                    user_input = match.group(1)
                    conversations[current_session].append({"role": "user", "content": user_input})
            
            # 提取字段填充
            if '字段填充' in line:
                match = re.search(r'字段填充：(\w+) = (.+?) \(', line)
                if match and current_session:
                    field = match.group(1)
                    value = match.group(2)
                    # 记录为系统推断
                    conversations[current_session].append({
                        "role": "system",
                        "content": f"【字段填充】{field} = {value}"
                    })
            
            # 提取提问
            if 'V4.3 提问' in line:
                match = re.search(r'question=(.+?)\.\.\.', line)
                if match and current_session:
                    question = match.group(1)
                    conversations[current_session].append({
                        "role": "ai",
                        "content": question
                    })
            
            # 提取报告生成
            if '触发报告生成' in line and current_session:
                conversations[current_session].append({
                    "role": "system",
                    "content": "【报告生成】触发报告生成流程"
                })
    
    return conversations

def generate_detailed_report(conversations):
    """生成详细报告"""
    report = "# V4.5.3 十案例完整对话流程\n\n"
    report += "**测试时间**: 2026-03-11 09:34-09:44\n"
    report += "**测试版本**: V4.5.3\n"
    report += "**测试类型**: 质量验证（完整对话记录）\n\n"
    report += "---\n\n"
    
    for i, case in enumerate(TEST_CASES):
        report += f"## 案例{i+1}: {case['name']}\n\n"
        report += f"**预期功能**: {case['expected']}\n"
        report += f"**用户输入**: \"{case['input']}\"\n\n"
        
        # 查找对应会话（简化处理，按顺序匹配）
        session_ids = list(conversations.keys())
        if i < len(session_ids):
            session_id = session_ids[i]
            conv = conversations[session_id]
            
            report += f"**会话 ID**: {session_id}\n\n"
            report += "### 对话流程\n\n"
            
            turn_count = 0
            for msg in conv[:20]:  # 限制显示 20 条
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                
                if role == 'user':
                    turn_count += 1
                    report += f"**第{turn_count}轮 - 用户**: {content}\n\n"
                elif role == 'ai':
                    report += f"**AI 提问**: {content}\n\n"
                elif role == 'system':
                    if '字段填充' in content:
                        report += f"📝 {content}\n\n"
                    elif '报告生成' in content:
                        report += f"✅ {content}\n\n"
            
            if len(conv) > 20:
                report += f"... (还有{len(conv)-20}条记录)\n\n"
        else:
            report += "**会话记录**: 未找到\n\n"
        
        report += "---\n\n"
    
    return report

def main():
    print("="*60)
    print("提取完整对话流程")
    print("="*60)
    
    # 提取对话
    conversations = extract_conversations()
    print(f"✅ 提取到 {len(conversations)} 个会话")
    
    # 生成详细报告
    report = generate_detailed_report(conversations)
    
    # 保存
    report_file = OUTPUT_DIR / "完整对话流程.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"✅ 详细报告：{report_file}")
    
    # 保存 JSON
    json_file = OUTPUT_DIR / "对话记录.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON 记录：{json_file}")
    
    # 复制到桌面
    import shutil
    desktop_file = Path("/home/admin/Desktop/10 案例完整对话流程.md")
    shutil.copy(report_file, desktop_file)
    print(f"📋 已复制到：{desktop_file}")

if __name__ == "__main__":
    main()
