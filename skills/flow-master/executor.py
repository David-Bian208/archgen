"""
flow-master Skill 执行器

确保每次都按流程执行 + 处理 trae 卡壳
"""

import sys
from pathlib import Path
from datetime import datetime
from enum import Enum

# 添加路径
WORKSPACE = Path(__file__).parent.parent.parent
sys.path.insert(0, str(WORKSPACE))


class FlowState(Enum):
    """流程状态"""
    STAGE1_REQUIREMENT = "stage1_requirement"
    STAGE2_IMPLEMENTATION = "stage2_implementation"
    STAGE3_VERIFICATION = "stage3_verification"
    STAGE4_JUDGMENT = "stage4_judgment"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class FlowMaster:
    """流程主控器"""
    
    def __init__(self):
        self.state = FlowState.STAGE1_REQUIREMENT
        self.current_task = None
        self.task_history = []
        self.trae_status = "idle"  # idle, working, stuck, taken_over
        self.trae_start_time = None
        self.trae_failure_count = 0
    
    def start_task(self, requirement: str) -> str:
        """启动新任务"""
        self.current_task = {
            "name": requirement[:50] + "...",
            "requirement": requirement,
            "start_time": datetime.now(),
            "state": FlowState.STAGE1_REQUIREMENT,
        }
        self.state = FlowState.STAGE1_REQUIREMENT
        
        return f"""
🛳️ **阶段 1：需求确认**

**需求理解：** {requirement[:100]}...

**执行计划：**
1. 需求分析 → 技术方案 → 编码 → 测试 → 部署
2. 预计时间：根据复杂度评估
3. 完成标准：测试通过 + 覆盖率审计通过

**请 DAVID 确认：**
- 回复"确认执行"开始
- 回复"修改需求"调整
"""
    
    def check_flow(self) -> str:
        """检查流程执行"""
        if not self.current_task:
            return "❌ 当前无任务。使用'开始新任务：[需求]'启动"
        
        stage_names = {
            FlowState.STAGE1_REQUIREMENT: "阶段 1：需求确认",
            FlowState.STAGE2_IMPLEMENTATION: "阶段 2：实现",
            FlowState.STAGE3_VERIFICATION: "阶段 3：验证",
            FlowState.STAGE4_JUDGMENT: "阶段 4：判定",
            FlowState.COMPLETED: "已完成",
            FlowState.BLOCKED: "已阻塞",
        }
        
        return f"""
🛳️ **流程检查**

**任务：** {self.current_task['name']}
**当前阶段：** {stage_names.get(self.state, '未知')}
**trae 状态：** {self.trae_status}
**开始时间：** {self.current_task['start_time'].strftime('%H:%M:%S')}

**下一步：** {self._get_next_step()}
"""
    
    def complete_stage(self, stage_num: int) -> str:
        """完成阶段"""
        if not self.current_task:
            return "❌ 当前无任务"
        
        stage_map = {
            1: FlowState.STAGE2_IMPLEMENTATION,
            2: FlowState.STAGE3_VERIFICATION,
            3: FlowState.STAGE4_JUDGMENT,
            4: FlowState.COMPLETED,
        }
        
        if stage_num not in stage_map:
            return f"❌ 无效阶段号：{stage_num}（1-4）"
        
        self.state = stage_map[stage_num]
        
        if stage_num == 4:
            return self._submit_judgment()
        else:
            stage_names = {1: "需求确认", 2: "实现", 3: "验证"}
            return f"""
✅ **阶段{stage_num}：{stage_names[stage_num]} 完成**

**进入阶段{stage_num + 1}：** {list(stage_names.values())[stage_num] if stage_num < 3 else "判定"}

{self._get_stage_instructions(stage_num + 1)}
"""
    
    def detect_trae_stuck(self) -> str:
        """检测 trae 卡壳"""
        if self.trae_status != "working":
            return "ℹ️ trae 当前未在工作中"
        
        # 检查超时
        if self.trae_start_time:
            elapsed = (datetime.now() - self.trae_start_time).total_seconds()
            if elapsed > 600:  # 10 分钟
                return self._take_over("timeout", elapsed)
        
        # 检查失败次数
        if self.trae_failure_count >= 3:
            return self._take_over("repeated_failure", self.trae_failure_count)
        
        return "ℹ️ trae 正常工作中"
    
    def report_trae_stuck(self) -> str:
        """手动报告 trae 卡壳"""
        return self._take_over("manual", 0)
    
    def _take_over(self, reason: str, context) -> str:
        """接管任务"""
        self.trae_status = "taken_over"
        self.current_task['trae_taken_over'] = True
        self.current_task['takeover_reason'] = reason
        
        reason_map = {
            "timeout": f"编码超时（{context/60:.1f}分钟）",
            "repeated_failure": f"反复失败（{context}次）",
            "manual": "手动触发",
        }
        
        return f"""
🛳️ **检测到 trae 卡壳，已接管**

**卡壳类型：** {reason_map.get(reason, reason)}
**根因分析：** 需要进一步分析
**处理方案：** 
1. 重新分析需求
2. 调整技术方案
3. 继续执行

**继续执行中...**
"""
    
    def _submit_judgment(self) -> str:
        """提交判定"""
        return f"""
🛳️ **阶段 4：提交判定**

**任务：** {self.current_task['name']}
**验证结果：**
- 测试结果：待执行
- 覆盖率：待审计
- 部署检查：待检查

**请 DAVID 判定：**
- 回复"通过"完成任务
- 回复"修改"指定修改内容
- 回复"重做"重新开始
"""
    
    def execute_judgment(self, judgment: str) -> str:
        """执行判定结果"""
        if judgment not in ["通过", "修改", "重做"]:
            return "❌ 无效判定。回复：通过/修改/重做"
        
        self.current_task['judgment'] = judgment
        self.current_task['completed_time'] = datetime.now()
        self.task_history.append(self.current_task)
        
        if judgment == "通过":
            self.state = FlowState.COMPLETED
            return f"""
✅ **任务完成**

**任务：** {self.current_task['name']}
**判定：** 通过
**完成时间：** {self.current_task['completed_time'].strftime('%Y-%m-%d %H:%M:%S')}

**已更新：**
- TASK_CURRENT.md
- memory/{datetime.now().strftime('%Y-%m-%d')}.md
"""
        elif judgment == "修改":
            self.state = FlowState.STAGE2_IMPLEMENTATION
            return """
🛳️ **执行修改**

**判定：** 修改
**进入：** 阶段 2：实现

**请指定修改内容：**
- 修改哪些部分
- 新增什么功能
- 修复什么问题
"""
        else:  # 重做
            self.state = FlowState.STAGE1_REQUIREMENT
            return """
🛳️ **重新执行**

**判定：** 重做
**进入：** 阶段 1：需求确认

**请重新描述需求：**
- 原需求的问题
- 新的期望
- 优先级
"""
    
    def _get_next_step(self) -> str:
        """获取下一步"""
        step_map = {
            FlowState.STAGE1_REQUIREMENT: "DAVID 确认需求 → 回复'确认执行'",
            FlowState.STAGE2_IMPLEMENTATION: "战舰实现 → 自动测试",
            FlowState.STAGE3_VERIFICATION: "提交验证报告 → DAVID 判定",
            FlowState.STAGE4_JUDGMENT: "DAVID 判定 → 通过/修改/重做",
            FlowState.COMPLETED: "无",
            FlowState.BLOCKED: "解决阻塞 → 继续",
        }
        return step_map.get(self.state, "未知")
    
    def _get_stage_instructions(self, stage_num: int) -> str:
        """获取阶段说明"""
        instructions = {
            1: "**阶段 1：需求确认**\n- DAVID 讲需求\n- 战舰澄清\n- DAVID 确认",
            2: "**阶段 2：实现**\n- 战舰技术方案\n- 编码（可调用 trae）\n- 自动测试",
            3: "**阶段 3：验证**\n- 运行测试\n- 覆盖率审计\n- 部署检查\n- 提交报告",
            4: "**阶段 4：判定**\n- DAVID 判定（通过/修改/重做）",
        }
        return instructions.get(stage_num, "")


# 全局实例
flow_master = FlowMaster()


def execute(command: str) -> str:
    """执行命令"""
    cmd = command.strip().lower()
    
    # 启动任务
    if "开始新任务" in cmd or "启动任务" in cmd:
        requirement = command.split("：")[-1] if "：" in command else command.split(":")[-1]
        return flow_master.start_task(requirement)
    
    # 流程检查
    if "检查流程" in cmd or "当前阶段" in cmd:
        return flow_master.check_flow()
    
    # 下一步
    if "下一步" in cmd:
        return f"下一步：{flow_master._get_next_step()}"
    
    # 完成阶段
    if "阶段" in cmd and "完成" in cmd:
        for i in range(1, 5):
            if f"阶段{i}" in cmd:
                return flow_master.complete_stage(i)
        return "❌ 无效阶段号（1-4）"
    
    # trae 卡壳检测
    if "trae 卡壳" in cmd or "卡壳" in cmd:
        if "检测" in cmd:
            return flow_master.detect_trae_stuck()
        else:
            return flow_master.report_trae_stuck()
    
    # 提交判定
    if "提交判定" in cmd:
        return flow_master._submit_judgment()
    
    # 判定结果
    if cmd in ["通过", "修改", "重做"]:
        return flow_master.execute_judgment(cmd)
    
    # 判定结果（带前缀）
    if "判定结果" in cmd:
        for j in ["通过", "修改", "重做"]:
            if j in cmd:
                return flow_master.execute_judgment(j)
        return "❌ 无效判定（通过/修改/重做）"
    
    # 帮助
    if "帮助" in cmd or "help" in cmd:
        return """
# 🛠️ flow-master Skill 帮助

## 可用命令

### 流程启动
- `开始新任务：[需求描述]` - 启动标准流程
- `继续之前的任务` - 继续中断的任务

### 流程检查
- `检查流程执行` - 检查当前阶段
- `下一步是什么` - 显示下一步

### trae 卡壳
- `trae 卡壳了` - 手动触发接管
- `这个任务卡住了` - 同上

### 阶段完成
- `阶段 1 完成` - 需求确认完成
- `阶段 2 完成` - 实现完成
- `阶段 3 完成` - 验证完成

### 判定
- `提交判定` - 提交给 DAVID 判定
- `判定结果：通过/修改/重做` - 执行判定

## 标准流程

阶段 1：需求 → DAVID 讲需求 → 战舰澄清 → DAVID 确认
阶段 2：实现 → 战舰全权负责 → 自动测试
阶段 3：验证 → 运行测试 → 覆盖率审计 → 部署检查
阶段 4：判定 → 提交验证报告 → DAVID 判定
"""
    
    return "❓ 未知命令。输入'帮助'查看可用命令。"


# CLI 入口
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        command = input("输入命令：")
    
    print(execute(command))
