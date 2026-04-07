"""
OpenClaw 工作流编排器 (Workflow Orchestrator)

灵感来源：claw-code 项目的 runtime.py + oh-my-codex (OmX) 工作流模式
用途：多代理协作、持久执行、输出审查

核心模式：
1. COLLABORATE - 多子代理并行协作（类似 OmX $team 模式）
2. PERSISTENT - 持续执行循环（类似 OmX $ralph 模式）
3. REVIEW - 输出审查（质量保证）

使用方式：
    from workspace.workflow_orchestrator import WorkflowOrchestrator
    
    orchestrator = WorkflowOrchestrator()
    
    # 多代理协作
    result = orchestrator.collaborate(
        task="分析这个代码库的架构",
        agents=["agent-1", "agent-2", "agent-3"]
    )
    
    # 持久执行
    result = orchestrator.persistent(
        task="重构这个模块",
        max_turns=10
    )
    
    # 输出审查
    result = orchestrator.review(
        output=report_text,
        criteria=["准确性", "完整性", "可读性"]
    )
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CollaborateResult:
    """多代理协作结果"""
    task: str
    agent_results: Dict[str, Any]
    merged_output: str
    execution_time_seconds: float
    success: bool
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task": self.task,
            "agent_count": len(self.agent_results),
            "merged_output": self.merged_output,
            "execution_time_seconds": self.execution_time_seconds,
            "success": self.success,
            "errors": self.errors,
        }


@dataclass(frozen=True)
class PersistentResult:
    """持久执行结果"""
    task: str
    turns: int
    history: List[Dict[str, Any]]
    final_output: str
    completed: bool
    stop_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task": self.task,
            "turns": self.turns,
            "final_output": self.final_output,
            "completed": self.completed,
            "stop_reason": self.stop_reason,
        }


@dataclass(frozen=True)
class ReviewResult:
    """审查结果"""
    output: str
    criteria_results: Dict[str, Any]
    overall_score: float
    suggestions: List[str]
    passed: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "criteria_results": self.criteria_results,
            "overall_score": self.overall_score,
            "suggestions": self.suggestions,
            "passed": self.passed,
        }


class WorkflowOrchestrator:
    """
    工作流编排器
    
    提供三种工作模式：
    1. collaborate - 多子代理并行协作
    2. persistent - 持续执行循环
    3. review - 输出审查
    """
    
    def __init__(self, sessions_spawn_fn: Optional[Callable] = None):
        """
        初始化编排器
        
        Args:
            sessions_spawn_fn: sessions_spawn 函数（用于实际执行）
        """
        self.sessions_spawn_fn = sessions_spawn_fn
        self._execution_history: List[Dict[str, Any]] = []
        logger.info("WorkflowOrchestrator 初始化完成")
    
    def collaborate(self, task: str, agents: List[str], timeout_seconds: int = 300) -> CollaborateResult:
        """
        多子代理并行协作（类似 OmX $team 模式）
        
        核心思想：将复杂任务分解给多个子代理同时执行，然后合并结果
        
        Args:
            task: 任务描述
            agents: 代理 ID 列表
            timeout_seconds: 超时秒数
            
        Returns:
            CollaborateResult: 协作结果
        """
        logger.info(f"COLLABORATE 模式：任务='{task[:50]}...', 代理数={len(agents)}")
        
        start_time = datetime.now()
        agent_results = {}
        errors = []
        
        # 如果没有实际的 sessions_spawn_fn，使用模拟执行
        if self.sessions_spawn_fn is None:
            logger.warning("未提供 sessions_spawn_fn，使用模拟执行")
            for agent_id in agents:
                agent_results[agent_id] = {
                    "status": "simulated",
                    "output": f"代理 {agent_id} 的模拟输出",
                    "timestamp": datetime.now().isoformat(),
                }
            
            merged_output = self._merge_collaborate_results(task, agent_results)
            
            result = CollaborateResult(
                task=task,
                agent_results=agent_results,
                merged_output=merged_output,
                execution_time_seconds=0.0,
                success=True,
                errors=errors,
            )
        else:
            # 实际执行：并行 spawn 多个子代理
            import concurrent.futures
            
            def run_agent(agent_id: str) -> tuple:
                try:
                    result = self.sessions_spawn_fn(
                        task=task,
                        agentId=agent_id,
                        timeoutSeconds=timeout_seconds,
                        cleanup="keep",
                    )
                    return (agent_id, result, None)
                except Exception as e:
                    return (agent_id, None, str(e))
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(agents)) as executor:
                futures = {executor.submit(run_agent, agent_id): agent_id for agent_id in agents}
                
                for future in concurrent.futures.as_completed(futures):
                    agent_id, result, error = future.result()
                    
                    if error:
                        errors.append(f"代理 {agent_id} 执行失败：{error}")
                        agent_results[agent_id] = {"status": "error", "error": error}
                    else:
                        agent_results[agent_id] = {"status": "success", "output": result}
            
            merged_output = self._merge_collaborate_results(task, agent_results)
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            result = CollaborateResult(
                task=task,
                agent_results=agent_results,
                merged_output=merged_output,
                execution_time_seconds=execution_time,
                success=len(errors) == 0,
                errors=errors,
            )
        
        # 记录执行历史
        self._execution_history.append({
            "mode": "collaborate",
            "task": task,
            "agents": agents,
            "success": result.success,
            "timestamp": datetime.now().isoformat(),
        })
        
        logger.info(f"COLLABORATE 完成：成功={result.success}, 执行时间={result.execution_time_seconds:.2f}s")
        return result
    
    def persistent(self, task: str, max_turns: int = 10, completion_threshold: float = 0.9) -> PersistentResult:
        """
        持续执行循环（类似 OmX $ralph 模式）
        
        核心思想：持续执行任务直到完成或达到最大轮次，强调"完成度纪律"
        
        Args:
            task: 任务描述
            max_turns: 最大轮次
            completion_threshold: 完成度阈值（0-1）
            
        Returns:
            PersistentResult: 持久执行结果
        """
        logger.info(f"PERSISTENT 模式：任务='{task[:50]}...', 最大轮次={max_turns}")
        
        history = []
        current_task = task
        completed = False
        stop_reason = None
        
        for turn in range(1, max_turns + 1):
            logger.info(f"PERSISTENT 轮次 {turn}/{max_turns}")
            
            # 执行当前轮次
            if self.sessions_spawn_fn is None:
                # 模拟执行
                turn_result = {
                    "turn": turn,
                    "status": "simulated",
                    "output": f"轮次 {turn} 的模拟输出",
                    "completion_estimate": min(0.3 * turn, 1.0),  # 模拟完成度增长
                }
            else:
                # 实际执行
                try:
                    result = self.sessions_spawn_fn(
                        task=current_task,
                        timeoutSeconds=300,
                        cleanup="keep",
                    )
                    turn_result = {
                        "turn": turn,
                        "status": "success",
                        "output": result,
                        "completion_estimate": self._estimate_completion(result),
                    }
                except Exception as e:
                    turn_result = {
                        "turn": turn,
                        "status": "error",
                        "error": str(e),
                        "completion_estimate": 0.0,
                    }
            
            history.append(turn_result)
            
            # 检查是否完成
            completion = turn_result.get("completion_estimate", 0.0)
            if completion >= completion_threshold:
                completed = True
                stop_reason = "completion_threshold_reached"
                logger.info(f"PERSISTENT 完成：完成度={completion:.2%}")
                break
            
            # 准备下一轮任务
            if turn < max_turns:
                current_task = f"继续上一步任务，当前进度：{turn_result.get('output', '')[:200]}..."
        
        # 确定停止原因
        if not stop_reason:
            stop_reason = "max_turns_reached" if not completed else stop_reason
        
        # 合并最终输出
        final_output = self._merge_persistent_history(history)
        
        result = PersistentResult(
            task=task,
            turns=len(history),
            history=history,
            final_output=final_output,
            completed=completed,
            stop_reason=stop_reason,
        )
        
        # 记录执行历史
        self._execution_history.append({
            "mode": "persistent",
            "task": task,
            "turns": len(history),
            "completed": completed,
            "timestamp": datetime.now().isoformat(),
        })
        
        logger.info(f"PERSISTENT 完成：轮次={len(history)}, 完成={completed}, 原因={stop_reason}")
        return result
    
    def review(self, output: str, criteria: List[str], min_score: float = 0.7) -> ReviewResult:
        """
        输出审查（质量保证）
        
        核心思想：使用子代理对输出进行多维度审查，确保质量
        
        Args:
            output: 待审查的输出
            criteria: 审查标准列表
            min_score: 最低通过分数
            
        Returns:
            ReviewResult: 审查结果
        """
        logger.info(f"REVIEW 模式：输出长度={len(output)}, 审查标准={len(criteria)}")
        
        criteria_results = {}
        all_suggestions = []
        
        for criterion in criteria:
            if self.sessions_spawn_fn is None:
                # 模拟审查
                criteria_results[criterion] = {
                    "score": 0.85,
                    "passed": True,
                    "feedback": f"模拟审查：{criterion} 通过",
                    "suggestions": [],
                }
            else:
                # 实际审查
                try:
                    review_task = f"请审查以下输出是否符合'{criterion}'标准：\n\n{output[:2000]}..."
                    result = self.sessions_spawn_fn(
                        task=review_task,
                        timeoutSeconds=120,
                        cleanup="delete",
                    )
                    
                    # 解析审查结果（假设返回 JSON）
                    review_data = self._parse_review_result(result)
                    criteria_results[criterion] = review_data
                    
                    if review_data.get("suggestions"):
                        all_suggestions.extend(review_data["suggestions"])
                    
                except Exception as e:
                    criteria_results[criterion] = {
                        "score": 0.0,
                        "passed": False,
                        "feedback": f"审查失败：{str(e)}",
                        "suggestions": [f"重新审查 {criterion}"],
                    }
                    all_suggestions.append(f"重新审查 {criterion}")
        
        # 计算总体分数
        scores = [r["score"] for r in criteria_results.values() if "score" in r]
        overall_score = sum(scores) / len(scores) if scores else 0.0
        
        # 判断是否通过
        passed = overall_score >= min_score and all(r.get("passed", False) for r in criteria_results.values())
        
        result = ReviewResult(
            output=output[:500] + "..." if len(output) > 500 else output,
            criteria_results=criteria_results,
            overall_score=overall_score,
            suggestions=list(set(all_suggestions)),  # 去重
            passed=passed,
        )
        
        # 记录执行历史
        self._execution_history.append({
            "mode": "review",
            "output_length": len(output),
            "criteria": criteria,
            "overall_score": overall_score,
            "passed": passed,
            "timestamp": datetime.now().isoformat(),
        })
        
        logger.info(f"REVIEW 完成：分数={overall_score:.2%}, 通过={passed}")
        return result
    
    def _merge_collaborate_results(self, task: str, agent_results: Dict[str, Any]) -> str:
        """合并多代理协作结果"""
        lines = [
            f"# 多代理协作结果",
            f"",
            f"**任务：** {task}",
            f"**代理数：** {len(agent_results)}",
            f"",
        ]
        
        for agent_id, result in agent_results.items():
            lines.append(f"## 代理 {agent_id}")
            lines.append("")
            if isinstance(result, dict):
                lines.append(f"状态：{result.get('status', 'unknown')}")
                if "output" in result:
                    lines.append(f"输出：{result['output'][:500]}")
            else:
                lines.append(f"输出：{str(result)[:500]}")
            lines.append("")
        
        lines.extend([
            "---",
            "",
            "**合并说明：** 以上是各代理的独立输出，需要根据任务需求进一步整合。",
        ])
        
        return "\n".join(lines)
    
    def _merge_persistent_history(self, history: List[Dict[str, Any]]) -> str:
        """合并持久执行历史"""
        lines = [
            f"# 持久执行结果",
            f"",
            f"**总轮次：** {len(history)}",
            f"",
        ]
        
        for turn_result in history:
            lines.append(f"## 轮次 {turn_result.get('turn', '?')}")
            lines.append(f"状态：{turn_result.get('status', 'unknown')}")
            if "output" in turn_result:
                lines.append(f"输出：{turn_result['output'][:300]}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _estimate_completion(self, result: Any) -> float:
        """估计完成度（简化实现）"""
        # 实际实现应该分析结果内容
        return 0.5  # 默认 50%
    
    def _parse_review_result(self, result: Any) -> Dict[str, Any]:
        """解析审查结果"""
        # 实际实现应该解析 JSON
        return {
            "score": 0.8,
            "passed": True,
            "feedback": "审查通过",
            "suggestions": [],
        }
    
    def get_execution_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取执行历史"""
        return self._execution_history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_executions": len(self._execution_history),
            "by_mode": {},
        }
        
        for entry in self._execution_history:
            mode = entry.get("mode", "unknown")
            stats["by_mode"][mode] = stats["by_mode"].get(mode, 0) + 1
        
        return stats


# ========== 全局单例 ==========

_orchestrator_instance: Optional[WorkflowOrchestrator] = None


def get_workflow_orchestrator() -> WorkflowOrchestrator:
    """获取全局编排器实例"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = WorkflowOrchestrator()
    return _orchestrator_instance


# ========== CLI 入口 ==========

if __name__ == "__main__":
    orchestrator = get_workflow_orchestrator()
    
    print("🎭 OpenClaw 工作流编排器")
    print("=" * 50)
    
    # 测试 COLLABORATE 模式
    print("\n📦 测试 COLLABORATE 模式...")
    result = orchestrator.collaborate(
        task="分析这个代码库的架构",
        agents=["agent-1", "agent-2"],
    )
    print(f"成功：{result.success}, 代理数：{len(result.agent_results)}")
    
    # 测试 PERSISTENT 模式
    print("\n🔄 测试 PERSISTENT 模式...")
    result = orchestrator.persistent(
        task="重构这个模块",
        max_turns=3,
    )
    print(f"完成：{result.completed}, 轮次：{result.turns}, 原因：{result.stop_reason}")
    
    # 测试 REVIEW 模式
    print("\n🔍 测试 REVIEW 模式...")
    result = orchestrator.review(
        output="这是一份测试报告...",
        criteria=["准确性", "完整性", "可读性"],
    )
    print(f"通过：{result.passed}, 分数：{result.overall_score:.2%}")
    
    # 显示统计
    print("\n📊 执行统计")
    stats = orchestrator.get_statistics()
    print(f"总执行次数：{stats['total_executions']}")
    print(f"按模式分布：{stats['by_mode']}")
