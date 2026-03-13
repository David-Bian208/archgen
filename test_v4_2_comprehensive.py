#!/usr/bin/env python3
"""
V4.2 完整修复验收测试

测试目标：
1. 【P0】报告完整性：所有章节必须有内容，特别是"行为模式解读"
2. 【P1】信息整合：摘要应综合所有对话关键信息，而非复制首条消息
3. 【P2】协商结束：系统应询问用户确认后再结束

测试案例：室内跳操发呆（包含"广播音乐"、"老师通常不干预"、"提醒后反应不一致"等关键点）
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/v4"

# 测试案例：室内跳操发呆
TEST_CASE = {
    "name": "室内跳操发呆",
    "conversation": [
        "孩子做操时有时会发呆",  # 首条消息
        "环境安静，其他小朋友认真做",  # 环境信息
        "眼神迷茫，好像在找提示",  # 关键：提示依赖
        "不看老师就做不好，会停下来",  # 关键：不看 + 做不好
        "是的，需要老师提醒才继续",  # 确认提示依赖
        "老师会走到他身边，拍拍他肩膀",  # 回应方式
        "广播音乐在放，但他好像没听到",  # 关键：广播音乐
        "老师通常不干预，除非他完全停下",  # 关键：老师通常不干预
        "提醒后有时反应快，有时慢",  # 关键：反应不一致
        "没有了，就这些",  # 确认结束
    ]
}

def run_test():
    print("=" * 80)
    print("V4.2 完整修复验收测试")
    print("=" * 80)
    print()
    
    session_id = None
    turn_count = 0
    locked_hypothesis = None
    completed = False
    confirmation_asked = False
    report_data = None
    
    for i, user_input in enumerate(TEST_CASE["conversation"], 1):
        turn_count = i
        print(f"【第 {i} 轮】")
        print(f"用户：{user_input}")
        
        # 发送请求
        try:
            response = requests.post(
                f"{BASE_URL}/chat",
                json={
                    "session_id": session_id,
                    "user_input": user_input
                },
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ API 请求失败：{response.status_code}")
                print(response.text)
                return False
            
            data = response.json()
            
        except Exception as e:
            print(f"❌ 请求异常：{e}")
            return False
        
        # 解析响应
        session_id = data.get("session_id")
        status = data.get("status")
        message = data.get("message", "")
        state = data.get("state", "N/A")
        current_locked = data.get("locked_hypothesis")
        response_type = data.get("response_type", "unknown")
        
        # 跟踪假设锁定
        if current_locked and not locked_hypothesis:
            locked_hypothesis = current_locked
            print(f"🔒 锁定假设：{locked_hypothesis}")
        
        # 检查是否询问确认（V4.2 新增）
        if response_type == "confirmation" or "还有没有其他" in message or "需要补充" in message:
            confirmation_asked = True
            print(f"✅ V4.2 修复：系统询问用户确认")
        
        # 检查是否完成
        if status == "completed":
            completed = True
            print(f"✅ 对话完成 (第 {i} 轮)")
            print()
            
            # 获取报告数据
            report_data = data.get("data", {})
            
            # ========== 【P0】报告完整性检查 ==========
            print("=" * 80)
            print("📊 【P0】报告完整性检查")
            print("=" * 80)
            
            report = report_data.get("report", {})
            
            # 检查摘要
            summary = report.get("summary", "")
            print(f"\n1. 摘要字段：{'✅ 存在' if summary else '❌ 空白'}")
            if summary:
                print(f"   内容：{summary[:100]}...")
            
            # 检查临床鉴别
            clinical_diff = report.get("clinical_differential", "")
            print(f"2. 临床鉴别字段：{'✅ 存在' if clinical_diff else '❌ 空白'}")
            
            # 检查行为模式解读（核心修复点）
            primary_hyp = report.get("primary_hypothesis", "")
            supporting_evidence = report.get("supporting_evidence", "")
            core_capability = report.get("core_capability_goal", "")
            
            print(f"3. 行为模式解读章节:")
            print(f"   - 主要假设：{'✅ ' + primary_hyp if primary_hyp else '❌ 空白'}")
            print(f"   - 支持证据：{'✅ ' + supporting_evidence[:50] if supporting_evidence else '❌ 空白'}...")
            print(f"   - 核心能力目标：{'✅ ' + core_capability[:50] if core_capability else '❌ 空白'}...")
            
            # 检查干预计划
            intervention_plan = report_data.get("intervention_plan", {})
            four_step = intervention_plan.get("four_step_plan", {}) if intervention_plan else {}
            
            print(f"4. 干预计划四步结构:")
            if four_step:
                print(f"   - 核心思路：{'✅' if four_step.get('core_idea') else '❌'}")
                print(f"   - 我们的计划：{'✅' if four_step.get('our_plan') else '❌'}")
                print(f"   - 成功的画面：{'✅' if four_step.get('success_picture') else '❌'}")
                print(f"   - 第一步行动：{'✅' if four_step.get('first_step') else '❌'}")
            else:
                print(f"   ❌ 四步结构缺失")
            
            # ========== 【P1】信息整合检查 ==========
            print()
            print("=" * 80)
            print("📊 【P1】信息整合检查")
            print("=" * 80)
            
            # 检查摘要是否包含关键信息
            key_info_found = []
            if summary:
                if "广播" in summary or "音乐" in summary:
                    key_info_found.append("广播音乐")
                if "老师" in summary:
                    key_info_found.append("老师")
                if "提醒" in summary:
                    key_info_found.append("提醒")
                if "反应" in summary or "不一致" in summary or "有时" in summary:
                    key_info_found.append("反应不一致")
            
            print(f"\n关键信息整合检查:")
            print(f"   期望包含：广播音乐、老师、提醒、反应不一致")
            print(f"   实际找到：{', '.join(key_info_found) if key_info_found else '无'}")
            
            # 检查是否只是复制首条消息
            first_message = TEST_CASE["conversation"][0]
            if summary and summary.strip() == first_message.strip():
                print(f"   ❌ 摘要机械复制首条消息")
            elif summary and len(summary) > len(first_message) * 1.5:
                print(f"   ✅ 摘要综合了多轮对话信息")
            else:
                print(f"   ⚠️  摘要长度较短，可能未充分整合")
            
            # ========== 【P2】协商结束检查 ==========
            print()
            print("=" * 80)
            print("📊 【P2】协商结束检查")
            print("=" * 80)
            
            print(f"\n确认询问：{'✅ 已询问' if confirmation_asked else '❌ 未询问（单方面结束）'}")
            
            # 总体结果
            print()
            print("=" * 80)
            print("📋 总体验收结果")
            print("=" * 80)
            
            p0_pass = bool(summary and primary_hyp and supporting_evidence and core_capability)
            p1_pass = len(key_info_found) >= 2 and (summary and len(summary) > len(first_message))
            p2_pass = confirmation_asked
            
            print(f"\n【P0】报告完整性：{'✅ 通过' if p0_pass else '❌ 失败'}")
            print(f"   - 所有章节有内容：{'✅' if p0_pass else '❌'}")
            
            print(f"【P1】信息整合：{'✅ 通过' if p1_pass else '❌ 失败'}")
            print(f"   - 关键信息整合：{len(key_info_found)}/4 项")
            print(f"   - 非机械复制：{'✅' if p1_pass else '❌'}")
            
            print(f"【P2】协商结束：{'✅ 通过' if p2_pass else '❌ 失败'}")
            print(f"   - 确认询问：{'✅' if p2_pass else '❌'}")
            
            all_pass = p0_pass and p1_pass and p2_pass
            
            print()
            if all_pass:
                print("🎉 所有验收检查通过！V4.2 修复成功！")
                return True
            else:
                print("⚠️  部分检查未通过，需要进一步调整")
                if not p0_pass:
                    print("   - P0 失败：报告章节仍有空白")
                if not p1_pass:
                    print("   - P1 失败：信息整合不足")
                if not p2_pass:
                    print("   - P2 失败：未询问用户确认")
                return False
        
        # 输出 AI 回应
        if status != "completed":
            print(f"AI: {message[:150]}..." if len(message) > 150 else f"AI: {message}")
            print(f"状态：{state}, 锁定：{current_locked or '无'}, 类型：{response_type}")
            print()
    
    # 如果循环结束但未完成
    if not completed:
        print("=" * 80)
        print("❌ 测试未完成：对话未在预期轮次内结束")
        print("=" * 80)
        return False
    
    return True


if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)
