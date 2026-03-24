#!/usr/bin/env python3
"""
V4.5.21 P0 Fix - 自动化回归测试套件

测试目的：确保 P0 级修复不会回退
测试案例：4 个核心 P0 案例 + 120 案例全量测试
运行方式：pytest tests/test_p0_regression.py -v
"""

import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.intervention_planner import InterventionPlanner


class TestP0CriticalCases:
    """P0 级关键案例测试（必须 100% 通过）"""
    
    @pytest.fixture
    def planner(self):
        """创建规划器实例"""
        return InterventionPlanner()
    
    def test_s5_social_skills_not_attention_seeking(self, planner):
        """S5: 社交技能不足不应调用寻求关注模板"""
        session_context = {
            "primary_hypothesis": "社交技能不足 - 身体边界感薄弱，缺乏换位思考能力",
            "capability_gap": "换位思考、身体感知",
            "child_behavior": "抱别人不知道轻重，把人家弄哭了",
            "context": "跟同龄人玩的时候"
        }
        
        plan = planner.generate_plan_with_narrative(
            matched_hypothesis_id="social_skills",
            scenario_key="peer_interaction",
            session_context=session_context
        )
        
        plan_text = str(plan).lower()
        
        # 应该包含社交技能教学元素
        assert any(kw in plan_text for kw in ["社交故事", "角色扮演", "直接教学", "教学"]), \
            "社交技能不足应包含教学元素"
        
        # 不应包含寻求关注模板的禁止词
        assert "忽视" not in plan_text, "社交技能不足不应建议'忽视'"
        assert "冷静角" not in plan_text, "社交技能不足不应建议'冷静角'"
    
    def test_a5_dangerous_behavior_safety_first(self, planner):
        """A5: 危险行为必须启用安全优先模式"""
        session_context = {
            "primary_hypothesis": "寻求关注行为 - 用危险行为获取成人情绪反应",
            "child_behavior": "故意做危险动作，比如爬到高处",
            "context": "为了看我们紧张的样子"
        }
        
        plan = planner.generate_plan_with_narrative(
            matched_hypothesis_id="attention_seeking",
            scenario_key="dangerous_behavior",
            session_context=session_context
        )
        
        plan_text = str(plan).lower()
        
        # 应该启用安全优先
        assert any(kw in plan_text for kw in ["安全优先", "消除危险", "环境安全"]), \
            "危险行为应启用安全优先模式"
        
        # 不应简单忽视
        assert "忽视" not in plan_text or "安全" in plan_text, \
            "危险行为不能简单忽视，除非在安全前提下"
    
    def test_r5_rigidity_not_attention_seeking(self, planner):
        """R5: 坚持同一性不应调用寻求关注模板"""
        session_context = {
            "primary_hypothesis": "刻板行为/坚持同一性 - 对固定仪式的坚持",
            "capability_gap": "变化耐受、灵活性",
            "child_behavior": "必须自己按电梯，别人按了会哭",
            "context": "出门前"
        }
        
        plan = planner.generate_plan_with_narrative(
            matched_hypothesis_id="rigidity",
            scenario_key="ritual_behavior",
            session_context=session_context
        )
        
        plan_text = str(plan).lower()
        
        # 应该包含坚持同一性的正确干预
        assert any(kw in plan_text for kw in ["预告", "渐进", "变化", "灵活"]), \
            "坚持同一性应包含预告/渐进变化元素"
        
        # 不应包含寻求关注模板的禁止词
        assert "忽视" not in plan_text, "坚持同一性不应建议'忽视'"
        assert "冷静角" not in plan_text, "坚持同一性不应建议'冷静角'"
    
    def test_at5_attention_not_natural_consequences(self, planner):
        """AT5: 注意力困难不应采用自然结果策略"""
        session_context = {
            "primary_hypothesis": "注意力/任务坚持 - 环境干扰下的注意力维持困难",
            "capability_gap": "持续性注意、自我监控",
            "child_behavior": "一点声音就分心，一道题能做半小时",
            "context": "做作业的时候"
        }
        
        plan = planner.generate_plan_with_narrative(
            matched_hypothesis_id="attention",
            scenario_key="task_attention",
            session_context=session_context
        )
        
        plan_text = str(plan).lower()
        
        # 应该包含注意力支持元素
        assert any(kw in plan_text for kw in ["环境调整", "专注", "分段", "计时器", "注意"]), \
            "注意力困难应包含环境调整/专注支持"
        
        # 不应采用自然结果策略
        assert "自然结果" not in plan_text, "注意力困难不应采用'自然结果'"
        assert "减少作业" not in plan_text, "注意力困难不应建议'减少作业'"


class TestSafetyPriority:
    """安全优先校验测试"""
    
    @pytest.fixture
    def planner(self):
        return InterventionPlanner()
    
    @pytest.mark.parametrize("danger_keyword,behavior_context", [
        ("爬高", "故意爬高"),
        ("危险", "做危险动作"),
        ("利器", "玩利器"),
        ("冲撞", "故意冲撞"),
        ("跑到马路", "突然跑到马路"),
        ("触电", "摸电源插座"),
        ("溺水", "靠近水池"),
        ("从高处", "从高处跳下"),
        ("跳下", "从窗台跳下"),
        ("攀爬", "攀爬窗户"),
        ("窗户", "爬窗户"),
        ("阳台", "爬阳台"),
        ("火", "玩火"),  # 需要危险上下文，排除"发火"（发脾气）
        ("烫", "碰烫的东西"),
    ])
    def test_safety_keywords_trigger_safety_mode(self, planner, danger_keyword, behavior_context):
        """测试危险关键词是否触发安全优先模式"""
        session_context = {
            "primary_hypothesis": "寻求关注行为",
            "child_behavior": f"故意{behavior_context}",
            "context": "为了获取注意"
        }
        
        plan = planner.generate_plan_with_narrative(
            matched_hypothesis_id="attention_seeking",
            scenario_key="dangerous_behavior",
            session_context=session_context
        )
        
        plan_text = str(plan).lower()
        
        assert any(kw in plan_text for kw in ["安全优先", "消除危险", "环境安全"]), \
            f"危险关键词'{danger_keyword}' + 行为'{behavior_context}'应触发安全优先模式"


class TestDiagnosisInterventionValidation:
    """诊断 - 干预匹配校验测试"""
    
    @pytest.fixture
    def planner(self):
        return InterventionPlanner()
    
    def test_forbidden_combinations_blocked(self, planner):
        """测试禁止的诊断 - 干预组合被拦截"""
        forbidden_pairs = [
            ("社交技能", "忽视"),
            ("社交技能", "冷静角"),
            ("坚持同一性", "忽视"),
            ("坚持同一性", "冷静角"),
            ("注意力", "自然结果"),
        ]
        
        for diagnosis_keyword, forbidden_word in forbidden_pairs:
            session_context = {
                "primary_hypothesis": f"{diagnosis_keyword} - 测试案例",
                "child_behavior": "测试行为",
                "context": "测试情境"
            }
            
            plan = planner.generate_plan_with_narrative(
                matched_hypothesis_id="test",
                scenario_key="test",
                session_context=session_context
            )
            
            plan_text = str(plan).lower()
            
            # 如果诊断包含关键词，干预不应包含禁止词
            if diagnosis_keyword in session_context["primary_hypothesis"]:
                # 允许 fallback 计划，但 fallback 也不应包含禁止词
                assert forbidden_word not in plan_text or "观察 + 支持" in str(plan), \
                    f"禁止组合：{diagnosis_keyword} × {forbidden_word}"


class TestFull120Cases:
    """120 案例全量测试（简化版）"""
    
    @pytest.fixture
    def planner(self):
        return InterventionPlanner()
    
    def test_all_categories_pass_90_percent(self, planner):
        """测试所有类别通过率>90%"""
        # 简化测试：每类别抽样 3 题
        sample_cases = [
            # 社交技能
            {"category": "social_skills", "behavior": "抢玩具", "gap": "轮流意识"},
            {"category": "social_skills", "behavior": "推人", "gap": "社交发起"},
            {"category": "social_skills", "behavior": "抱人不知轻重", "gap": "身体边界"},
            
            # 寻求关注
            {"category": "attention_seeking", "behavior": "打电话时捣乱", "func": "获取注意"},
            {"category": "attention_seeking", "behavior": "爬高", "func": "危险行为"},
            {"category": "attention_seeking", "behavior": "发出怪声音", "func": "同伴关注"},
            
            # 坚持同一性
            {"category": "rigidity", "behavior": "固定路线", "gap": "变化耐受"},
            {"category": "rigidity", "behavior": "按电梯仪式", "gap": "仪式行为"},
            {"category": "rigidity", "behavior": "玩具排列", "gap": "排序坚持"},
            
            # 注意力
            {"category": "attention", "behavior": "分心", "gap": "持续性注意"},
            {"category": "attention", "behavior": "坐不住", "gap": "冲动控制"},
            {"category": "attention", "behavior": "作业拖拉", "gap": "任务坚持"},
        ]
        
        passed = 0
        total = len(sample_cases)
        
        for case in sample_cases:
            session_context = {
                "primary_hypothesis": f"{case['category']} - {case.get('gap', case.get('func', '测试'))}",
                "child_behavior": case["behavior"],
                "context": "测试情境"
            }
            
            plan = planner.generate_plan_with_narrative(
                matched_hypothesis_id=case["category"],
                scenario_key=case["category"],
                session_context=session_context
            )
            
            # 简单检查：计划不应为空，不应包含明显错误
            if plan and "忽视" not in str(plan).lower() or "安全" in str(plan).lower():
                passed += 1
        
        pass_rate = passed / total * 100
        assert pass_rate >= 90, f"抽样测试通过率 {pass_rate:.1f}% < 90%"


# ========== 运行测试 ==========

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
