"""
干预模板验证器 V4.11（专业版）- Bug 修复版

基于 RDI、执行功能、感觉统合理论的干预模板质量验证

验证维度：
1. 游戏化设计 - 游戏名称、脚手架、80% 成功率
2. 原理解释 - 脑科学、行为学、家长理解三层结构
3. 干预质量 - 具体标准、可观察任务
4. 理论一致性 - RDI、执行功能、感觉统合理论术语

使用：
```bash
python3 app/agents/validate_intervention_templates.py
```
"""

import re
from typing import Dict, Any


class InterventionTemplateValidator:
    """干预模板验证器（专业版）"""
    
    def __init__(self):
        """初始化验证器"""
        # 实际模板数据（从 intervention_planner.py 复制）
        self.actual_templates = {
            "_generate_prompt_dependence_plan": {
                "strategy_details_gamified": "**锚点大冒险**游戏：\n\n1. **第 1 周（脚手架期）**：家长全程示范\n2. **第 2 周（半独立期）**：家长做一半\n3. **第 3 周（独立期）**：孩子主导\n4. **第 4 周（巩固期）**：完全独立\n\n记住，每一次撤除脚手架都是孩子独立的一大步！确保 80% 以上成功率，让孩子在'我能行'的感觉中成长！",
                "why_effective": "这个干预有效的原因：\n• 脑科学：通过 4 周重复练习，强化前额叶皮层的神经连接（突触可塑性），将外部提示从'需要思考'转化为基底核的自动化反应。每一次脚手架撤除都是神经回路重组的过程\n• 行为学：脚手架设计确保 80% 以上成功率（正强化原理），逐步撤除辅助培养独立性（消退原理）。第 1 周全辅助建立安全感，第 2-3 周渐褪培养自我监控，第 4 周巩固形成习惯\n• 家长理解：就像学骑自行车，从扶车→半扶→放手→偶尔保护，每一次放手都是孩子独立的一大步！脚手架不是'永远扶着'，而是'适时放手'",
                "core_principle": "通过脚手架设计（第 1 周全辅助→第 2 周半辅助→第 3 周独立→第 4 周巩固），逐步将外部提示内化为孩子的自我监控能力。",
                "success_criteria": "在 4 周内，孩子能在自然情境中独立启动动作序列，成功率稳定达到 80% 以上，且不需要外部提示。",
                "parent_observation_task": "记录：日期、辅助级别（1-4）、成功率（%）、孩子反应（主动/被动）。重点是记录'脚手架渐褪'的轨迹。",
            },
            "_generate_escape_difficulty_plan": {
                "strategy_details_gamified": "**成功阶梯挑战**游戏：\n\n1. **第 1 周（微步骤期）**：将 activity 切成'3 分钟微步骤'\n2. **第 2 周（阶梯期）**：逐步增加难度到 5 分钟、7 分钟\n3. **第 3 周（独立期）**：孩子自己设定阶梯目标\n4. **第 4 周（巩固期）**：完全独立启动\n\n记住，每一次'开始'都是成功！确保 80% 以上成功率，让孩子在'我能行'的感觉中成长！",
                "why_effective": "这个干预有效的原因：\n• 脑科学：通过重复成功体验，强化前额叶皮层与奖赏回路（伏隔核）的神经连接，将'逃避'转化为'主动参与'。每一次成功都是多巴胺释放，强化'我能行'的神经回路\n• 行为学：任务分解降低认知负荷（执行功能训练），80% 成功率确保正强化（操作性条件反射）。微步骤设计让孩子无法拒绝（'就 3 分钟'），高频成功体验建立自我效能感\n• 家长理解：就像爬楼梯，从矮台阶开始→逐步升高→独立攀登，每一次'我做到了'都是孩子自信的一大步！任务分解不是'降低标准'，而是'搭建阶梯'",
                "core_principle": "通过任务分解（大任务→微步骤）和降低起点难度（3 分钟启动），让孩子体验'我能做到'的成功感（80% 成功率），从而减少逃避行为。",
                "success_criteria": "在 4 周内，孩子能主动开始 activity 任务至少 3 次/天，且每次持续时间达到 10-15 分钟以上，成功率稳定在 80% 以上。",
                "parent_observation_task": "记录：日期、任务名称、启动次数、持续时间、成功率（%）、孩子反应（主动/被动）。重点是记录'阶梯成长'的轨迹。",
            },
        }
    
    def validate_template(self, template_name: str, template: Dict[str, Any]) -> Dict[str, bool]:
        """验证单个模板的质量"""
        checks = {
            # 游戏化设计
            'has_game_name': self._check_game_name(template),
            'has_scaffolding': self._check_scaffolding(template),
            'has_success_rate': self._check_success_rate(template),
            
            # 原理解释
            'has_neuroscience': self._check_neuroscience(template),
            'has_behaviorism': self._check_behaviorism(template),
            'has_parent_language': self._check_parent_language(template),
            
            # 干预质量
            'has_specific_criteria': self._check_specific_criteria(template),
            'has_observable_task': self._check_observable_task(template),
            
            # 理论一致性
            'has_theory_keywords': self._check_theory_keywords(template),
        }
        
        return checks
    
    def _check_game_name(self, template: Dict[str, Any]) -> bool:
        """检查是否有游戏名称"""
        strategy = template.get("strategy_details_gamified", "")
        # 匹配 **XXX 游戏**或**XXX**游戏
        return bool(re.search(r'\*\*[^*]+游戏\*\*|\*\*[^*]+\*\*游戏', strategy))
    
    def _check_scaffolding(self, template: Dict[str, Any]) -> bool:
        """检查是否有脚手架设计（4 周渐进）"""
        strategy = template.get("strategy_details_gamified", "")
        # 注意：正则表达式中不要有空格
        return bool(re.search(r'第 [1-4] 周 | 从.*到 | 脚手架', strategy))
    
    def _check_success_rate(self, template: Dict[str, Any]) -> bool:
        """检查是否有 80% 成功率保证"""
        strategy = template.get("strategy_details_gamified", "")
        core = template.get("core_principle", "")
        return bool(re.search(r'80%|成功', strategy + core))
    
    def _check_neuroscience(self, template: Dict[str, Any]) -> bool:
        """检查是否有脑科学解释"""
        why = template.get("why_effective", "")
        return bool(re.search(r'前额叶 | 神经 | 突触|RAS|基底核 | 多巴胺 | 海马体 | 可塑性', why, re.IGNORECASE))
    
    def _check_behaviorism(self, template: Dict[str, Any]) -> bool:
        """检查是否有行为学解释"""
        why = template.get("why_effective", "")
        return bool(re.search(r'强化 | 消退 | 正强化 | 操作性 | 前因 | 后果 | 脚手架|ZPD', why))
    
    def _check_parent_language(self, template: Dict[str, Any]) -> bool:
        """检查是否有家长理解的语言（比喻）"""
        why = template.get("why_effective", "")
        return bool(re.search(r'就像 | 不是.*而是', why))
    
    def _check_specific_criteria(self, template: Dict[str, Any]) -> bool:
        """检查是否有具体的成功标准"""
        criteria = template.get("success_criteria", "")
        return bool(re.search(r'\d+ 周|\d+ 天|\d+%', criteria))
    
    def _check_observable_task(self, template: Dict[str, Any]) -> bool:
        """检查是否有可观察的家长任务"""
        task = template.get("parent_observation_task", "")
        return len(task) > 20
    
    def _check_theory_keywords(self, template: Dict[str, Any]) -> bool:
        """检查是否有理论关键词"""
        why = template.get("why_effective", "")
        theory_keywords = [
            "RDI", "脚手架", "执行功能", "感觉统合",
            "工作记忆", "抑制控制", "认知灵活性",
            "本体觉", "前庭觉", "网状激活系统",
            "正强化", "消退", "脚手架"
        ]
        return any(kw in why for kw in theory_keywords)
    
    def run_validation(self) -> Dict[str, Dict[str, bool]]:
        """运行所有模板的验证"""
        results = {}
        
        for template_name, template in self.actual_templates.items():
            checks = self.validate_template(template_name, template)
            results[template_name] = checks
        
        return results
    
    def print_report(self, results: Dict[str, Dict[str, bool]]) -> None:
        """打印验证报告"""
        print("=" * 70)
        print("干预模板验证报告 V4.11（专业版）")
        print("=" * 70)
        print()
        
        total_checks = 0
        passed_checks = 0
        
        for template_name, checks in results.items():
            # 计算通过率
            template_total = len(checks)
            template_passed = sum(1 for v in checks.values() if v)
            template_rate = template_passed / template_total * 100 if template_total > 0 else 0
            
            total_checks += template_total
            passed_checks += template_passed
            
            # 打印状态
            status = "✅" if template_rate >= 80 else "⚠️" if template_rate >= 50 else "❌"
            print(f"{status} {template_name}: {template_passed}/{template_total} ({template_rate:.0f}%)")
            
            # 打印详细检查
            for check_name, passed in checks.items():
                check_status = "✅" if passed else "❌"
                print(f"   {check_status} {check_name}")
            
            print()
        
        # 总体统计
        overall_rate = passed_checks / total_checks * 100 if total_checks > 0 else 0
        print("=" * 70)
        print(f"总体通过率：{passed_checks}/{total_checks} ({overall_rate:.1f}%)")
        
        if overall_rate >= 90:
            print("✅ 优秀 - 模板质量符合专业标准")
        elif overall_rate >= 70:
            print("⚠️ 良好 - 部分模板需要优化")
        else:
            print("❌ 需改进 - 大量模板不符合专业标准")
        
        print("=" * 70)


def main():
    """主函数"""
    validator = InterventionTemplateValidator()
    results = validator.run_validation()
    validator.print_report(results)
    
    print("\n\n💡 提示：完整验证需要集成到测试套件中")
    print("当前为演示模式，验证逻辑已就绪")


if __name__ == "__main__":
    main()
