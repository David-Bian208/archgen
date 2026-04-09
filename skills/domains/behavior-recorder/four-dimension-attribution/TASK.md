# 四维度归因 Skill 实现任务

**版本：** 1.0.0  
**创建时间：** 2026-04-08  
**优先级：** P0  
**分配给：** TRAE  
**预计时间：** 30-45 分钟

---

## 📋 任务目标

**解决 LLM token 超限问题，实现四维度归因**

**预期效果：**
- ✅ JSON 解析成功率 >95%
- ✅ 响应时间 <15 秒
- ✅ 输出截断率 <5%
- ✅ 四维度覆盖率 >90%（Skill）

---

## 🚀 执行步骤

### Step 1: 创建 Skill 模块（P0）

**执行：** 按照 `IMPLEMENTATION.md` 创建完整 Skill

```bash
# 1. 创建目录
mkdir -p /home/admin/.openclaw/workspace/skills/domains/behavior-recorder/four-dimension-attribution/examples

# 2. 创建以下文件（参考 IMPLEMENTATION.md）：
# - SKILL.md
# - prompt.py
# - executor.py
# - test.py
# - examples/input_example.txt
# - examples/output_example.md

# 3. 运行测试
cd /home/admin/.openclaw/workspace/skills/domains/behavior-recorder/four-dimension-attribution
python3 test.py
```

**验收：** 4 个测试用例全部通过

---

### Step 2: 简化主系统提示词（P0）

**文件：** `behavior_recorder_service/app/agents/insight_analyzer.py`

**操作：** 找到四维度归因提示词（约 55 行），替换为：

```python
【V4.10.4 P0 临床推理核心逻辑 - 多环节协同】

分析行为背后的认知功能环节时，考虑多个可能相关的功能领域，
并说明它们如何协同导致观察到的行为。
用"齿轮啮合"比喻说明多环节协同作用。
```

**验收：**
- ✅ 提示词从 55 行减少到 3 行
- ✅ 保留"多环节协同"理念
- ✅ 移除强制 4 个维度的要求

---

### Step 3: 测试主系统稳定性（P0）

```bash
# 重启服务
sudo systemctl restart behavior-api

# 测试 JSON 解析
curl -X POST http://localhost:8001/api/v4/analyze \
  -H "Content-Type: application/json" \
  -d '{"user_input":"场景：在家玩小游戏。孩子的表现：她以为我看到盒子里还是糖，不太理解我看到的是薯片的意思。"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('✅ JSON 解析成功')"
```

**验收：**
- ✅ JSON 解析成功（无截断）
- ✅ 响应时间 <15 秒
- ✅ 连续测试 10 次成功率 >95%

---

### Step 4: 前端添加四维度选项（P1，可选）

**文件：** `behavior_recorder_service/frontend/App.vue`

**添加复选框：**
```vue
<label class="option-label">
  <input type="checkbox" v-model="includeFourDimensions">
  包含四维度归因分析（增加 5-10 秒等待时间）
</label>
```

**条件显示：**
```vue
<div v-if="report.four_dimension_attribution" class="four-dimension-section">
  <h3>🔍 行为背后的原因（四维度分析）</h3>
  <div v-html="formatMarkdown(report.four_dimension_attribution)"></div>
</div>
```

**验收：** 复选框正常显示，勾选后可调用 Skill

---

### Step 5: 集成测试（P1，可选）

**文件：** `behavior_recorder_service/tests/test_four_dimension_integration.py`

```python
#!/usr/bin/env python3
"""四维度归因集成测试"""

def test_skill_quality():
    """测试 Skill 四维度归因质量"""
    from skills.domains.behavior_recorder.four_dimension_attribution.executor import FourDimensionAnalyzer
    
    analyzer = FourDimensionAnalyzer()
    result = analyzer.analyze("她以为我看到盒子里还是糖，不太理解我看到的是薯片的意思。")
    
    assert result["success"] == True
    assert "心理理论" in result["attribution"]
    assert "执行功能" in result["attribution"]
    assert "齿轮" in result["attribution"]
    print("✅ Skill 质量测试通过")

def test_main_system_stability():
    """测试主系统稳定性（简化后）"""
    import requests
    
    response = requests.post(
        "http://localhost:8001/api/v4/analyze",
        json={"user_input": "场景：在家玩小游戏。孩子的表现：她以为我看到盒子里还是糖。"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data is not None
    print("✅ 主系统稳定性测试通过")

if __name__ == "__main__":
    test_skill_quality()
    test_main_system_stability()
    print("\n🎉 所有集成测试通过")
```

**验收：** 集成测试通过

---

### Step 6: Git 提交（P0）

```bash
cd /home/admin/.openclaw/workspace

# 添加 Skill 模块
git add skills/domains/behavior-recorder/four-dimension-attribution/

# 添加主系统修改
git add behavior_recorder_service/app/agents/insight_analyzer.py

# 添加前端修改（如果有）
git add behavior_recorder_service/frontend/App.vue

# 添加测试（如果有）
git add behavior_recorder_service/tests/test_four_dimension_integration.py

# 提交
git commit -m "feat(skills): 新增四维度归因 Skill + 简化主系统（V4.10.4）

核心改进:
- 创建独立的四维度归因 Skill 模块
- 简化主系统提示词（55 行→3 行），解决 token 超限问题
- 主流程与深度分析解耦，用户可按需选择
- 包含完整测试用例（4 个场景）

效果:
- JSON 解析成功率：<50% → >95%
- 响应时间：>30 秒 → <15 秒
- 输出截断率：>30% → <5%

文件列表:
- skills/domains/behavior-recorder/four-dimension-attribution/*
- app/agents/insight_analyzer.py (简化)
- frontend/App.vue (可选：四维度选项)
- tests/test_four_dimension_integration.py (可选：集成测试)

Refs: V4.10.4 临床推理框架升级"
```

---

## ✅ 验收标准

| 检查项 | 标准 | 验证方法 |
|--------|------|----------|
| **Skill 模块** | 完整 | `ls -la skills/domains/behavior-recorder/four-dimension-attribution/` |
| **Skill 测试** | 4 用例全部通过 | `python3 test.py` |
| **主系统简化** | 55 行→3 行 | `grep -A5 "多环节协同" app/agents/insight_analyzer.py` |
| **JSON 解析** | 成功率>95% | 连续测试 10 次 |
| **响应时间** | <15 秒 | 计时测试 |
| **输出截断** | <5% | 人工审查 |
| **Git 提交** | 信息清晰 | `git log --oneline -1` |

---

## 📊 预期效果对比

| 指标 | 修改前 | 修改后 | 改善 |
|------|--------|--------|------|
| JSON 解析成功率 | <50% | >95% | +90% |
| 响应时间 | >30 秒（超时） | <15 秒 | -50% |
| 输出截断率 | >30% | <5% | -83% |
| 四维度覆盖率 | N/A | >90%（Skill） | ✅ |
| 用户可选择 | ❌ | ✅ | ✅ |

---

## 📁 参考文档

- `IMPLEMENTATION.md` - Skill 完整实现指南
- `SKILL.md` - Skill 描述文档（创建后）

---

**完成后通知：** @战舰  
**优先级：** P0（Step 1-3 必须执行，Step 4-5 可选）
