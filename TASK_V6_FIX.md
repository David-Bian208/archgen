# 任务：V6.0 干预建议重复问题修复（P0 级）

**优先级：** P0  
**负责人：** trae（分配给小治-后端）  
**截止日期：** 2026-04-02  

---

## 任务描述

**问题：** 两个完全不同的能力缺口得到了相同的干预建议

| 案例 | 能力缺口 | 期望干预 | 实际干预 | 状态 |
|------|----------|----------|----------|------|
| 玥玥 | 社交信号监测弱 | 社交信号监测训练 | ❌ 我们开始玩了吗信号练习 | 错误 |
| OK | 观点采择困难 | 观点采择训练 | ❌ 我们开始玩了吗信号练习 | 错误 |

**影响：** 分析正确但开错药，严重削弱专业可信度

---

## 根因分析（架构师已诊断）

**问题文件：** `behavior_recorder_service/app/agents/intervention_planner.py`

**问题方法：** `_generate_social_skills_plan()`

**根因：**
1. 没有优先使用 `capability_gap` 字段
2. 场景匹配条件过于宽泛（如 `"以为" in child_behavior` 匹配太多场景）
3. 导致不同能力缺口被错误匹配到相同干预

---

## 修复方案（架构师已设计）

### 核心逻辑：能力缺口优先匹配

在 `_generate_social_skills_plan()` 方法中实现以下匹配逻辑：

```python
# 在 _generate_social_skills_plan() 中
if capability_gap:
    # 1. 社交信号监测（优先检查，避免被覆盖）
    if any(kw in capability_gap for kw in ["社交信号", "监测", "观察反应", "眼神接触", "非语言"]):
        game_name = "社交信号侦探游戏"
        # ... 设置 game_steps 和 why_effective
    
    # 2. 观点采择（纯观点采择案例）
    elif any(kw in capability_gap for kw in ["观点采择", "换位思考", "视角转换", "心理理论", "他人视角", "自我中心"]):
        game_name = "视角游戏：妈妈会看到什么"
        # ... 设置 game_steps 和 why_effective
    
    # 3. 工作记忆
    elif any(kw in capability_gap for kw in ["工作记忆", "记不住", "忘记步骤", "多步骤", "序列记忆"]):
        game_name = "视觉提示卡游戏"
    
    # 4. 认知灵活性
    elif any(kw in capability_gap for kw in ["认知灵活性", "灵活性", "变化", "转换", "固守"]):
        game_name = "规则变变变游戏"
    
    # 5. 情绪识别
    elif any(kw in capability_gap for kw in ["情绪识别", "表情", "面部表情", "情绪"]):
        game_name = "情绪小侦探游戏"
    
    # 6. 共同调控
    elif any(kw in capability_gap for kw in ["共同调控", "同步", "节奏匹配", "互动", "轮流"]):
        game_name = "我们开始玩了吗信号练习"
    
    else:
        # 未匹配到具体能力缺口，降级到场景匹配
        game_name, game_steps, why_effective = self._match_social_scene(child_behavior)
else:
    # 无能力缺口信息，降级到场景匹配
    game_name, game_steps, why_effective = self._match_social_scene(child_behavior)
```

### 新增辅助方法

新增 `_match_social_scene()` 方法处理降级场景匹配：

```python
def _match_social_scene(self, child_behavior: str) -> tuple[str, str, str]:
    """场景匹配辅助方法（降级用）"""
    # 身体边界场景
    if "拥抱" in child_behavior or "轻重" in child_behavior:
        return "轻柔的手练习游戏", "...", "..."
    
    # 规则理解场景
    elif "规则" in child_behavior or "僵化" in child_behavior:
        return "规则变变变游戏", "...", "..."
    
    # 介绍/任务化场景
    elif "介绍" in child_behavior or "任务化" in child_behavior:
        return "说完看脸游戏", "...", "..."
    
    # 通用场景
    else:
        return "社交技能假装游戏", "...", "..."
```

---

## 完成标准（必须量化）

- [ ] 修改 `app/agents/intervention_planner.py`
  - [ ] 重构 `_generate_social_skills_plan()` 方法
  - [ ] 新增 `_match_social_scene()` 辅助方法
- [ ] 编写测试 `tests/test_v6_capability_matching.py`
  - [ ] 验证玥玥案例→社交信号侦探游戏
  - [ ] 验证 OK 案例→视角游戏
  - [ ] 验证两个案例得到不同干预
- [ ] 所有测试通过（pytest）
- [ ] 生成修复报告到 `/home/admin/Desktop/V6.0_干预建议重复问题修复报告.md`

---

## 测试用例（必须通过）

### 测试 1：玥玥案例
```python
capability_gap = "社交信号监测弱和观点采择应用困难"
child_behavior = "任务化的介绍，没有关注对方反应"
预期结果：社交信号侦探游戏 ✅
```

### 测试 2：OK 案例
```python
capability_gap = "观点采择能力：难以理解他人视角"
child_behavior = "以为别人看到的和自己一样"
预期结果：视角游戏：妈妈会看到什么 ✅
```

### 测试 3：差异化验证
```python
# 两个案例应该得到不同的干预
assert yueyue_game != ok_game ✅
```

---

## 技术方案说明

**能力缺口→干预映射表：**

| 能力缺口 | 匹配关键词 | 干预游戏 |
|---------|-----------|---------|
| 社交信号监测 | 社交信号、监测、观察反应、眼神接触 | 社交信号侦探游戏 |
| 观点采择 | 观点采择、换位思考、视角转换、心理理论 | 视角游戏：妈妈会看到什么 |
| 工作记忆 | 工作记忆、记不住、忘记步骤、多步骤 | 视觉提示卡游戏 |
| 认知灵活性 | 认知灵活性、灵活性、变化、转换 | 规则变变变游戏 |
| 情绪识别 | 情绪识别、表情、面部表情、情绪 | 情绪小侦探游戏 |
| 共同调控 | 共同调控、同步、节奏匹配、互动 | 我们开始玩了吗信号练习 |

**匹配顺序很重要：**
1. 社交信号监测（优先，避免被观点采择覆盖）
2. 观点采择
3. 其他能力缺口
4. 降级到场景匹配

---

## 执行记录（trae 填写）

- [ ] YYYY-MM-DD HH:MM - trae：开始执行
- [ ] YYYY-MM-DD HH:MM - trae：完成代码修改
- [ ] YYYY-MM-DD HH:MM - trae：完成测试编写
- [ ] YYYY-MM-DD HH:MM - trae：测试通过（X/X）
- [ ] YYYY-MM-DD HH:MM - trae：生成修复报告
- [ ] YYYY-MM-DD HH:MM - 战舰：代码审查通过
- [ ] YYYY-MM-DD HH:MM - 战舰：部署检查通过

---

## 审查清单（战舰用）

**代码审查：**
- [ ] 能力缺口匹配逻辑正确
- [ ] 匹配顺序合理（社交信号监测优先）
- [ ] 降级机制完整
- [ ] 代码风格符合现有规范

**测试审查：**
- [ ] 测试覆盖核心案例
- [ ] 测试可独立运行
- [ ] 测试断言清晰

**文档审查：**
- [ ] 修复报告完整
- [ ] 包含问题描述、根因、修复方案、测试结果

---

**创建人：** 战舰 🛳️（架构师）  
**创建时间：** 2026-04-02 14:30  
**最后更新：** 2026-04-02 14:30
