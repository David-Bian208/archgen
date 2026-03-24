#!/usr/bin/env python3
"""
V4.10.3 50 题家长风格测试

测试目标：
1. 模拟真实家长说话方式（口语化、非专业术语）
2. 覆盖 5 类核心场景（共同游戏、对话/介绍、规则变化、身体边界、情绪识别）
3. 验证系统回复的准确性、专业性和用户友好性
4. 生成完整测试报告

测试维度：
- 场景分类准确性
- 摘要质量（比喻、归因一致性）
- 临床推理结构（鉴别与排除、核心假设、能力缺口）
- 干预建议匹配度
- 格式化显示（加粗、列表）
"""

import json
import os
from datetime import datetime

# 50 个测试案例（模拟家长口语化表达）
TEST_CASES = [
    # ========== 共同游戏场景（10 题）==========
    {
        "id": 1,
        "scene": "joint_play",
        "parent_input": "我女儿跟小朋友玩的时候，总以为自己跟别人在玩，其实人家没带她玩。比如抓人游戏，一群孩子在那儿跑，她也在跑，觉得自己参与了，特别嗨，但其他孩子根本没跟她玩。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "社交信号监测弱"
    },
    {
        "id": 2,
        "scene": "joint_play",
        "parent_input": "游戏规则明明有好多条，我儿子只记得住 3 条，然后就反复说这 3 条。比如抓人游戏，他就只会说"你是鬼"，别人经过就施魔法，来回就这两句。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "认知灵活性不足"
    },
    {
        "id": 3,
        "scene": "joint_play",
        "parent_input": "孩子在游乐场想加入其他小朋友，但不知道怎么玩。他就站在旁边看，或者冲过去抢玩具，结果其他孩子都不跟他玩。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "社交信号监测弱"
    },
    {
        "id": 4,
        "scene": "joint_play",
        "parent_input": "我女儿玩滑梯的时候，别的小朋友在排队，她直接插队，还说"我们一起玩吧"，结果其他孩子都躲着她。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "观点采择困难"
    },
    {
        "id": 5,
        "scene": "joint_play",
        "parent_input": "孩子跟小朋友玩捉迷藏，他一直躲在同一个地方，别的孩子都换地方了他不换，结果每次都被找到，他还觉得很好玩。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "认知灵活性不足"
    },
    {
        "id": 6,
        "scene": "joint_play",
        "parent_input": "我儿子在幼儿园玩积木，别的孩子都在搭城堡，他一个人在旁边搭小汽车，老师说叫他加入他也不加入。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "社交信号监测弱"
    },
    {
        "id": 7,
        "scene": "joint_play",
        "parent_input": "孩子玩秋千，别的小朋友想玩，他不肯让，说"我先来的"，但其实他已经玩很久了。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "观点采择困难"
    },
    {
        "id": 8,
        "scene": "joint_play",
        "parent_input": "我女儿跟小朋友玩"过家家"，她一直当"妈妈"，不让别人当，结果其他孩子都不跟她玩了。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "社交灵活性不足"
    },
    {
        "id": 9,
        "scene": "joint_play",
        "parent_input": "孩子在公园玩沙子，别的孩子想加入，他把沙子扬起来说"这是我的"，然后其他孩子就走了。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "观点采择困难"
    },
    {
        "id": 10,
        "scene": "joint_play",
        "parent_input": "我儿子玩拼图，别的小朋友想一起玩，他把拼图藏起来说"我自己玩"，然后一个人拼了半天。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "社交信号监测弱"
    },
    
    # ========== 对话/介绍场景（10 题）==========
    {
        "id": 11,
        "scene": "conversation_intro",
        "parent_input": "我女儿给别人介绍朋友的时候，就像完成任务一样，说完"他叫小明，是我的好朋友"就走了，也不看人家有没有在听。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "社交信号监测弱"
    },
    {
        "id": 12,
        "scene": "conversation_intro",
        "parent_input": "孩子跟别人说话的时候，说完自己的就不管了，也不问别人问题，就站在那里等，也不知道该干嘛。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "观点采择困难"
    },
    {
        "id": 13,
        "scene": "conversation_intro",
        "parent_input": "我儿子跟小朋友聊天，就一直说自己喜欢什么，也不听别人说，别人想插话他也停不下来。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "社交信号监测弱"
    },
    {
        "id": 14,
        "scene": "conversation_intro",
        "parent_input": "孩子问别人问题，人家还没回答完，他就又问下一个，感觉就是走个形式，不是真的想知道答案。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "社交信号监测弱"
    },
    {
        "id": 15,
        "scene": "conversation_intro",
        "parent_input": "我女儿给别人看她的画，展示完就问"好看吗"，人家说"好看"她就走了，也不解释画的是什么。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "观点采择困难"
    },
    {
        "id": 16,
        "scene": "conversation_intro",
        "parent_input": "孩子跟别人说话的时候，眼睛不看对方，就看别的地方，说完就走，感觉特别敷衍。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "社交信号监测弱"
    },
    {
        "id": 17,
        "scene": "conversation_intro",
        "parent_input": "我儿子跟小朋友打招呼，说完"你好"就没了下文，就站着等，也不知道该说什么。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "社交信号监测弱"
    },
    {
        "id": 18,
        "scene": "conversation_intro",
        "parent_input": "孩子给别人讲故事，讲完就问"讲完了"，也不看人家想不想听，也不问人家有没有听懂。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "观点采择困难"
    },
    {
        "id": 19,
        "scene": "conversation_intro",
        "parent_input": "我女儿跟别人分享玩具，说"给你玩"，然后把玩具递过去就走了，也不教人家怎么玩。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "观点采择困难"
    },
    {
        "id": 20,
        "scene": "conversation_intro",
        "parent_input": "孩子跟别人道歉，说完"对不起"就完了，也不看人家接不接受，就觉得自己已经道歉了。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "社交信号监测弱"
    },
    
    # ========== 规则变化场景（10 题）==========
    {
        "id": 21,
        "scene": "rules_rigidity",
        "parent_input": "我儿子每天回家必须走同一条路，有一次换了条路走，他就崩溃大哭，说"不对不对"。",
        "expected_hypothesis": "坚持同一性",
        "expected_capability_gap": "认知灵活性不足"
    },
    {
        "id": 22,
        "scene": "rules_rigidity",
        "parent_input": "孩子吃饭必须用同一个碗，有一次用了别的碗，他就不吃，说"这不是我的碗"。",
        "expected_hypothesis": "坚持同一性",
        "expected_capability_gap": "认知灵活性不足"
    },
    {
        "id": 23,
        "scene": "rules_rigidity",
        "parent_input": "我女儿睡觉前必须先把玩具排好，有一次我帮她收了，她就哭，说"不是这样排的"。",
        "expected_hypothesis": "坚持同一性",
        "expected_capability_gap": "认知灵活性不足"
    },
    {
        "id": 24,
        "scene": "rules_rigidity",
        "parent_input": "孩子穿衣服必须按特定顺序，先穿袜子再穿裤子，有一次我先给他穿裤子，他就脱了重新穿。",
        "expected_hypothesis": "坚持同一性",
        "expected_capability_gap": "认知灵活性不足"
    },
    {
        "id": 25,
        "scene": "rules_rigidity",
        "parent_input": "我儿子看电视必须看同一集，反复看，有一次我换了下一集，他就发脾气，说"还要看这个"。",
        "expected_hypothesis": "坚持同一性",
        "expected_capability_gap": "认知灵活性不足"
    },
    {
        "id": 26,
        "scene": "rules_rigidity",
        "parent_input": "孩子画画必须用同一支笔，有一次笔没水了，他就不用别的笔，就不画了。",
        "expected_hypothesis": "坚持同一性",
        "expected_capability_gap": "认知灵活性不足"
    },
    {
        "id": 27,
        "scene": "rules_rigidity",
        "parent_input": "我女儿出门必须自己按电梯按钮，有一次我按了，她就让我重新按，她来按。",
        "expected_hypothesis": "坚持同一性",
        "expected_capability_gap": "认知灵活性不足"
    },
    {
        "id": 28,
        "scene": "rules_rigidity",
        "parent_input": "孩子玩玩具必须按颜色分类，有一次我帮他混在一起了，他就全部倒出来重新分。",
        "expected_hypothesis": "坚持同一性",
        "expected_capability_gap": "认知灵活性不足"
    },
    {
        "id": 29,
        "scene": "rules_rigidity",
        "parent_input": "我儿子洗澡必须先用沐浴露再用洗发水，有一次顺序反了，他就说"不对"，要重新洗。",
        "expected_hypothesis": "坚持同一性",
        "expected_capability_gap": "认知灵活性不足"
    },
    {
        "id": 30,
        "scene": "rules_rigidity",
        "parent_input": "孩子吃饭必须坐同一个位置，有一次坐了别的位置，他就不吃，说"这不是我的位置"。",
        "expected_hypothesis": "坚持同一性",
        "expected_capability_gap": "认知灵活性不足"
    },
    
    # ========== 身体边界场景（10 题）==========
    {
        "id": 31,
        "scene": "body_boundary",
        "parent_input": "我女儿抱小朋友的时候特别用力，把人家的肋骨都勒疼了，她还觉得自己是在友好。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "身体边界感不足"
    },
    {
        "id": 32,
        "scene": "body_boundary",
        "parent_input": "孩子跟别人说话的时候站得特别近，都快贴到人家脸上了，人家一直往后退。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "身体边界感不足"
    },
    {
        "id": 33,
        "scene": "body_boundary",
        "parent_input": "我儿子拍别人肩膀，下手没轻没重的，把人家都拍疼了，他还觉得是在打招呼。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "身体边界感不足"
    },
    {
        "id": 34,
        "scene": "body_boundary",
        "parent_input": "孩子玩的时候老是推到别人，他不是故意的，就是不知道控制力度，老是撞到人。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "身体边界感不足"
    },
    {
        "id": 35,
        "scene": "body_boundary",
        "parent_input": "我女儿喜欢摸别人的脸，人家都躲开了她还摸，说"我就摸一下"。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "身体边界感不足"
    },
    {
        "id": 36,
        "scene": "body_boundary",
        "parent_input": "孩子跟小朋友玩的时候，老是靠得太近，人家都在玩游戏，他就贴在人家背后看。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "身体边界感不足"
    },
    {
        "id": 37,
        "scene": "body_boundary",
        "parent_input": "我儿子拉别人的手，拉得特别紧，人家想挣脱他还拉得更紧，说"别走"。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "身体边界感不足"
    },
    {
        "id": 38,
        "scene": "body_boundary",
        "parent_input": "孩子玩闹的时候不知道轻重，把人家都弄哭了，他还觉得是在玩，不知道人家疼。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "身体边界感不足"
    },
    {
        "id": 39,
        "scene": "body_boundary",
        "parent_input": "我女儿坐别人腿上，人家都说不坐了，她还要坐，说"我就要坐"。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "身体边界感不足"
    },
    {
        "id": 40,
        "scene": "body_boundary",
        "parent_input": "孩子跟别人抢玩具，直接上手拽，把人家手都拽红了，也不知道松手。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "身体边界感不足"
    },
    
    # ========== 情绪识别场景（10 题）==========
    {
        "id": 41,
        "scene": "emotion_recognition",
        "parent_input": "我儿子跟小朋友玩，人家都皱眉了他还继续，最后人家生气走了，他还不知道怎么回事。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "情绪识别困难"
    },
    {
        "id": 42,
        "scene": "emotion_recognition",
        "parent_input": "孩子给别人看东西，人家都说"不要不要"了，他还一直给人家看，看不懂人家不想看。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "情绪识别困难"
    },
    {
        "id": 43,
        "scene": "emotion_recognition",
        "parent_input": "我女儿说话的时候，人家都打哈欠了，她还在那儿说，不知道人家已经不想听了。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "情绪识别困难"
    },
    {
        "id": 44,
        "scene": "emotion_recognition",
        "parent_input": "孩子跟别人开玩笑，人家都生气了，他还觉得人家在笑，看不懂人家的表情。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "情绪识别困难"
    },
    {
        "id": 45,
        "scene": "emotion_recognition",
        "parent_input": "我儿子看到别人哭，还过去笑，人家哭得更厉害了，他也不知道自己哪里做错了。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "情绪识别困难"
    },
    {
        "id": 46,
        "scene": "emotion_recognition",
        "parent_input": "孩子跟小朋友玩，人家都说"我不玩了"，他还拉着人家玩，不知道人家是真的不想玩了。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "情绪识别困难"
    },
    {
        "id": 47,
        "scene": "emotion_recognition",
        "parent_input": "我女儿给别人看她的画，人家说"不好看"，她就哭了，不知道人家可能是开玩笑的。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "情绪识别困难"
    },
    {
        "id": 48,
        "scene": "emotion_recognition",
        "parent_input": "孩子跟别人说话，人家都看别的地方了，他还在那儿说，不知道人家已经不想听了。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "情绪识别困难"
    },
    {
        "id": 49,
        "scene": "emotion_recognition",
        "parent_input": "我儿子玩的时候，人家都皱眉了他还继续，最后人家都走了，他还不知道自己哪里做错了。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "情绪识别困难"
    },
    {
        "id": 50,
        "scene": "emotion_recognition",
        "parent_input": "孩子跟别人分享，人家都说"不要"，他还硬塞给人家，不知道人家是真的不想要。",
        "expected_hypothesis": "社交技能不足",
        "expected_capability_gap": "情绪识别困难"
    },
]


def generate_test_report(results, output_path):
    """生成测试报告"""
    
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    # 按场景统计
    scene_stats = {}
    for result in results:
        scene = result["scene"]
        if scene not in scene_stats:
            scene_stats[scene] = {"total": 0, "passed": 0}
        scene_stats[scene]["total"] += 1
        if result["passed"]:
            scene_stats[scene]["passed"] += 1
    
    report = f"""# V4.10.3 50 题家长风格测试报告

**测试日期：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**测试目标：** 验证系统在真实家长口语化表达下的表现  
**测试总数：** {total} 题  
**通过数量：** {passed} 题  
**通过率：** {pass_rate:.1f}%

---

## 一、整体评估

### 测试维度
1. **场景分类准确性** - 能否正确识别 5 类核心场景
2. **摘要质量** - 比喻是否生动、归因是否一致
3. **临床推理结构** - 是否包含鉴别与排除、核心假设、能力缺口分析
4. **干预建议匹配度** - 建议是否与场景和能力缺口匹配
5. **格式化显示** - 加粗、列表是否正确显示

### 测试结果
- ✅ **优秀** (pass_rate ≥ 95%)：系统可直接用于生产环境
- ⚠️ **良好** (85% ≤ pass_rate < 95%)：系统可用，建议优化
- ❌ **需改进** (pass_rate < 85%)：系统需要进一步修复

**本次评估：** { "✅ 优秀" if pass_rate >= 95 else ("⚠️ 良好" if pass_rate >= 85 else "❌ 需改进") }

---

## 二、按场景统计

| 场景类型 | 测试数量 | 通过数量 | 通过率 |
|----------|----------|----------|--------|
"""
    
    scene_names = {
        "joint_play": "共同游戏",
        "conversation_intro": "对话/介绍",
        "rules_rigidity": "规则变化",
        "body_boundary": "身体边界",
        "emotion_recognition": "情绪识别"
    }
    
    for scene, stats in scene_stats.items():
        scene_pass_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        report += f"| {scene_names.get(scene, scene)} | {stats['total']} | {stats['passed']} | {scene_pass_rate:.1f}% |\n"
    
    report += f"""
---

## 三、详细测试结果

### 通过案例 ({passed} 题)

"""
    
    for result in results:
        if result["passed"]:
            report += f"**#{result['id']}** {result['parent_input'][:50]}...\n\n"
    
    report += f"""
### 未通过案例 ({total - passed} 题)

"""
    
    for result in results:
        if not result["passed"]:
            report += f"**#{result['id']}** {result['parent_input'][:50]}...\n"
            report += f"- 预期假设：{result['expected_hypothesis']}\n"
            report += f"- 实际假设：{result['actual_hypothesis']}\n"
            report += f"- 预期能力缺口：{result['expected_capability_gap']}\n"
            report += f"- 实际能力缺口：{result['actual_capability_gap']}\n"
            report += f"- 失败原因：{result['failure_reason']}\n\n"
    
    report += f"""
---

## 四、改进建议

"""
    
    # 分析失败模式
    failure_patterns = {}
    for result in results:
        if not result["passed"]:
            pattern = result.get("failure_reason", "未知")[:50]
            if pattern not in failure_patterns:
                failure_patterns[pattern] = 0
            failure_patterns[pattern] += 1
    
    if failure_patterns:
        report += "### 主要失败模式\n\n"
        for pattern, count in sorted(failure_patterns.items(), key=lambda x: -x[1]):
            report += f"- {pattern} ({count} 次)\n"
    else:
        report += "✅ 无明显失败模式，系统表现稳定。\n"
    
    report += f"""
---

## 五、结论

"""
    
    if pass_rate >= 95:
        report += f"""**系统已达到生产环境标准！**

- ✅ 场景分类准确
- ✅ 摘要质量优秀（比喻生动、归因一致）
- ✅ 临床推理结构完整
- ✅ 干预建议匹配精准
- ✅ 格式化显示正确

**建议：** 可以直接发布 V4.10.3 正式版。
"""
    elif pass_rate >= 85:
        report += f"""**系统基本可用，建议优化后发布。**

- ✅ 核心功能正常
- ⚠️ 部分场景需要优化
- ⚠️ 个别案例需要修复

**建议：** 修复未通过案例后发布 V4.10.3 正式版。
"""
    else:
        report += f"""**系统需要进一步修复。**

- ❌ 核心功能存在缺陷
- ❌ 多个场景需要优化
- ❌ 需要系统性修复

**建议：** 暂停发布，优先修复失败案例。
"""
    
    report += f"""
---

**测试完成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**测试人员：** OpenClaw 自动化测试系统  
**备份文件：** behavior_recorder_V4.10.3_backup_{datetime.now().strftime('%Y%m%d')}.tar.gz
"""
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ 测试报告已生成：{output_path}")
    return report


if __name__ == "__main__":
    print("="*60)
    print("🧪 V4.10.3 50 题家长风格测试")
    print("="*60)
    print(f"\n测试案例数量：{len(TEST_CASES)}")
    print(f"测试开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "="*60)
    
    # 注意：这是测试数据定义文件
    # 实际测试需要调用 API 并分析响应
    # 这里只生成测试报告模板
    
    print("\n⚠️  注意：这是测试数据定义文件")
    print("实际测试需要：")
    print("1. 调用后端 API 发送每个测试案例")
    print("2. 解析系统响应")
    print("3. 比对预期结果")
    print("4. 生成测试报告")
    print("\n请按以下步骤执行测试：")
    print("1. 访问 http://localhost:3000")
    print("2. 手动测试前 5 个案例，验证系统表现")
    print("3. 如需自动化测试，请创建 API 测试脚本")
    print("\n" + "="*60)
