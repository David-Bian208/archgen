"""
V6.0 P0 能力缺口匹配测试

测试目标：验证不同能力缺口得到不同的干预建议
修复问题：玥玥案例和 OK 案例得到相同干预建议

测试案例：
1. 玥玥案例：社交技能不足 + 社交信号监测弱 → 应得到"社交信号侦探游戏"
2. OK 案例：社交技能不足 + 观点采择困难 → 应得到"视角游戏：妈妈会看到什么"
"""

import unittest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.intervention_planner import InterventionPlanner


class TestV6CapabilityMatching(unittest.TestCase):
    """V6.0 P0 能力缺口匹配测试"""
    
    def setUp(self):
        """测试前准备"""
        self.planner = InterventionPlanner()
    
    def test_yueyue_case_social_signal_monitoring(self):
        """
        玥玥案例测试：社交信号监测弱 → 社交信号侦探游戏
        
        案例背景：
        - 玥玥在游乐场想加入抓人游戏
        - 她以为小朋友在和她玩，但实际没有
        - 能力缺口：社交信号监测弱
        - 期望干预：社交信号侦探游戏
        """
        session_context = {
            "context": "游乐场抓人游戏",
            "child_behavior": "玥玥以为小朋友在和她玩，但实际没有",
            "capability_gap": "社交信号监测弱，难以观察同伴反应",
            "primary_hypothesis": "社交技能不足",
        }
        
        plan = self.planner._generate_social_skills_plan(session_context)
        
        # 验证干预游戏名称
        self.assertIsNotNone(plan)
        self.assertIn("four_step_plan", plan)
        
        # 核心验证：必须包含"社交信号侦探游戏"
        self.assertIn("社交信号侦探游戏", plan["four_step_plan"]["our_plan"])
        
        # 验证原理解释包含社交信号监测
        self.assertIn("why_effective", plan)
        self.assertIn("社交信号监测", plan["why_effective"])
        
        print("✅ 玥玥案例测试通过：社交信号监测弱 → 社交信号侦探游戏")
    
    def test_ok_case_perspective_taking(self):
        """
        OK 案例测试：观点采择困难 → 视角游戏：妈妈会看到什么
        
        案例背景：
        - OK 在类似情境下表现出观点采择困难
        - 能力缺口：观点采择困难
        - 期望干预：视角游戏：妈妈会看到什么
        """
        session_context = {
            "context": "社交互动场景",
            "child_behavior": "OK 难以理解他人的想法和感受",
            "capability_gap": "观点采择困难，难以换位思考",
            "primary_hypothesis": "社交技能不足",
        }
        
        plan = self.planner._generate_social_skills_plan(session_context)
        
        # 验证干预游戏名称
        self.assertIsNotNone(plan)
        self.assertIn("four_step_plan", plan)
        
        # 核心验证：必须包含"视角游戏：妈妈会看到什么"
        self.assertIn("视角游戏：妈妈会看到什么", plan["four_step_plan"]["our_plan"])
        
        # 验证原理解释包含观点采择
        self.assertIn("why_effective", plan)
        self.assertIn("观点采择", plan["why_effective"])
        
        print("✅ OK 案例测试通过：观点采择困难 → 视角游戏：妈妈会看到什么")
    
    def test_two_cases_different_interventions(self):
        """
        核心验证：两个案例必须得到不同的干预建议
        
        这是 P0 级修复的核心验收标准
        """
        # 玥玥案例
        yueyue_context = {
            "context": "游乐场抓人游戏",
            "child_behavior": "玥玥以为小朋友在和她玩，但实际没有",
            "capability_gap": "社交信号监测弱，难以观察同伴反应",
            "primary_hypothesis": "社交技能不足",
        }
        
        # OK 案例
        ok_context = {
            "context": "社交互动场景",
            "child_behavior": "OK 难以理解他人的想法和感受",
            "capability_gap": "观点采择困难，难以换位思考",
            "primary_hypothesis": "社交技能不足",
        }
        
        yueyue_plan = self.planner._generate_social_skills_plan(yueyue_context)
        ok_plan = self.planner._generate_social_skills_plan(ok_context)
        
        # 提取游戏名称
        yueyue_game = yueyue_plan["four_step_plan"]["our_plan"]
        ok_game = ok_plan["four_step_plan"]["our_plan"]
        
        # 核心验证：两个案例的游戏必须不同
        self.assertNotEqual(
            yueyue_game, 
            ok_game, 
            "❌ P0 级问题：两个不同能力缺口得到了相同的干预建议！"
        )
        
        # 验证各自得到正确的干预
        self.assertIn("社交信号侦探游戏", yueyue_game)
        self.assertIn("视角游戏：妈妈会看到什么", ok_game)
        
        print("✅ 核心验证通过：两个案例得到不同的干预建议")
        print(f"   玥玥案例 → {yueyue_plan['four_step_plan']['our_plan'].split('**')[1]}")
        print(f"   OK 案例 → {ok_plan['four_step_plan']['our_plan'].split('**')[1]}")
    
    def test_working_memory_gap(self):
        """测试工作记忆能力缺口匹配"""
        session_context = {
            "context": "多步骤任务",
            "child_behavior": "孩子经常忘记下一步要做什么",
            "capability_gap": "工作记忆弱，记不住多步骤指令",
            "primary_hypothesis": "社交技能不足",
        }
        
        plan = self.planner._generate_social_skills_plan(session_context)
        
        self.assertIn("视觉提示卡游戏", plan["four_step_plan"]["our_plan"])
        print("✅ 工作记忆测试通过：工作记忆弱 → 视觉提示卡游戏")
    
    def test_cognitive_flexibility_gap(self):
        """测试认知灵活性能力缺口匹配"""
        session_context = {
            "context": "规则变化场景",
            "child_behavior": "孩子无法接受规则变化",
            "capability_gap": "认知灵活性不足，难以适应变化",
            "primary_hypothesis": "社交技能不足",
        }
        
        plan = self.planner._generate_social_skills_plan(session_context)
        
        self.assertIn("规则变变变游戏", plan["four_step_plan"]["our_plan"])
        print("✅ 认知灵活性测试通过：认知灵活性不足 → 规则变变变游戏")
    
    def test_emotion_recognition_gap(self):
        """测试情绪识别能力缺口匹配"""
        session_context = {
            "context": "情绪识别场景",
            "child_behavior": "孩子无法识别他人的情绪表情",
            "capability_gap": "情绪识别困难，难以解读面部表情",
            "primary_hypothesis": "社交技能不足",
        }
        
        plan = self.planner._generate_social_skills_plan(session_context)
        
        self.assertIn("情绪小侦探游戏", plan["four_step_plan"]["our_plan"])
        print("✅ 情绪识别测试通过：情绪识别困难 → 情绪小侦探游戏")
    
    def test_co_regulation_gap(self):
        """测试共同调控能力缺口匹配"""
        session_context = {
            "context": "互动游戏场景",
            "child_behavior": "孩子难以与同伴同步互动节奏",
            "capability_gap": "共同调控能力弱，难以同步互动节奏",
            "primary_hypothesis": "社交技能不足",
        }
        
        plan = self.planner._generate_social_skills_plan(session_context)
        
        self.assertIn("我们开始玩了吗信号练习", plan["four_step_plan"]["our_plan"])
        print("✅ 共同调控测试通过：共同调控能力弱 → 我们开始玩了吗信号练习")
    
    def test_fallback_to_scene_matching(self):
        """测试降级到场景匹配（无 capability_gap 时）"""
        session_context = {
            "context": "游乐场抓人游戏",
            "child_behavior": "孩子以为小朋友在和她玩",
            "capability_gap": "",  # 空能力缺口
            "primary_hypothesis": "社交技能不足",
        }
        
        plan = self.planner._generate_social_skills_plan(session_context)
        
        # 应该降级到场景匹配，匹配到"以为"关键词
        self.assertIn("我们开始玩了吗信号练习", plan["four_step_plan"]["our_plan"])
        print("✅ 降级测试通过：无 capability_gap 时降级到场景匹配")


def run_tests():
    """运行测试并返回结果"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestV6CapabilityMatching)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果摘要
    return {
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "success": result.wasSuccessful()
    }


if __name__ == "__main__":
    print("=" * 60)
    print("V6.0 P0 能力缺口匹配测试")
    print("=" * 60)
    print()
    
    result = run_tests()
    
    print()
    print("=" * 60)
    print(f"测试结果：运行 {result['tests_run']} 个测试")
    print(f"成功：{result['tests_run'] - result['failures'] - result['errors']}")
    print(f"失败：{result['failures']}")
    print(f"错误：{result['errors']}")
    print("=" * 60)
    
    if result["success"]:
        print("✅ 所有测试通过！V6.0 P0 修复验证成功！")
        sys.exit(0)
    else:
        print("❌ 部分测试失败！请检查修复代码！")
        sys.exit(1)
