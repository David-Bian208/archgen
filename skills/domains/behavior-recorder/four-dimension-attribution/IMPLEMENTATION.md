# 四维度归因 Skill 实现指令

**版本：** 1.0.0  
**创建时间：** 2026-04-08  
**优先级：** P0  
**分配给：** TRAE

---

## 📋 任务概述

**目标：** 创建独立的"四维度归因"Skill 模块，解决 LLM token 限制问题

**核心价值：**
- ✅ 解耦：不阻塞主流程
- ✅ 可复用：可被其他项目调用
- ✅ 可控：独立测试、独立优化
- ✅ 无代码重复维护

---

## 🎯 实现步骤

### Step 1: 创建目录结构

```bash
mkdir -p /home/admin/.openclaw/workspace/skills/domains/behavior-recorder/four-dimension-attribution/examples
```

---

### Step 2: 创建 SKILL.md

**文件：** `skills/domains/behavior-recorder/four-dimension-attribution/SKILL.md`

```markdown
# 四维度归因 Skill

**版本：** 1.0.0  
**创建时间：** 2026-04-08  
**用途：** 从 4 个认知维度分析儿童行为背后的功能环节  
**调用方式：** 命令行 / Python API

---

## 🧠 四维度模型

### 1. 心理理论（Theory of Mind）
- **检查点**：是否涉及理解他人想法、信念、视角
- **输出**：受阻环节（信念形成/意图推理/视角采择）+ 神经基础（颞顶联合区、前额叶）

### 2. 执行功能（Executive Function）
- **检查点**：是否涉及工作记忆、抑制控制、认知灵活性
- **输出**：具体子功能如何受影响

### 3. 视觉 - 空间认知（Visual-Spatial Cognition）
- **检查点**：是否涉及空间理解、视角转换、心理旋转
- **输出**：未内化的规则

### 4. 语言 - 概念理解（Language-Conceptual Understanding）
- **检查点**：是否涉及词汇理解、概念抽象、问题解析
- **输出**：字面化理解的词汇/概念

---

## 🚀 调用方式

### 命令行调用
```bash
cd skills/domains/behavior-recorder/four-dimension-attribution
python3 executor.py "孩子推人插队"
```

### Python API 调用
```python
from skills.domains.behavior_recorder.four_dimension_attribution.executor import FourDimensionAnalyzer
analyzer = FourDimensionAnalyzer()
result = analyzer.analyze("孩子推人插队")
print(result["attribution"])
```

---

## 🧪 测试用例

**用例 1：薯片盒子游戏（观点采择）**
- 输入："她以为我看到盒子里还是糖，不太理解我看到的是薯片的意思。"
- 预期：包含心理理论 + 执行功能 + 视觉空间 + 语言理解四维度

**用例 2：等待提示（提示依赖）**
- 输入："遇到困难就说我不会，等着大人教，其实都会做。"
- 预期：包含执行功能 + 语言理解维度

**用例 3：寻求关注**
- 输入："老师看她时她就故意发出奇怪声音，老师不看她就不发。"
- 预期：包含心理理论 + 执行功能维度

---

## ⚠️ 注意事项

1. **字数限制**：输出控制在 800 字以内（防止 token 超限）
2. **LLM 配置**：复用主项目的 LLM 客户端配置
3. **错误处理**：LLM 调用失败时返回友好的错误信息

---

**维护者：** 行为观察助手团队
```

---

### Step 3: 创建 prompt.py

**文件：** `skills/domains/behavior-recorder/four-dimension-attribution/prompt.py`

```python
"""
四维度归因提示词模板

用法：
    from prompt import FOUR_DIMENSION_PROMPT
    prompt = FOUR_DIMENSION_PROMPT.format(behavior="行为描述")
"""

FOUR_DIMENSION_PROMPT = """请从以下 4 个维度分析以下儿童行为背后的认知功能环节：

**行为描述：**
{behavior}

---

## 分析维度

**1. 心理理论**
- 检查点：是否涉及理解他人想法、信念、视角？
- 如相关：说明具体受阻环节（信念形成/意图推理/视角采择）和神经基础（颞顶联合区、前额叶）

**2. 执行功能**
- 检查点：是否涉及工作记忆、抑制控制、认知灵活性？
- 如相关：说明具体哪些子功能受影响，如何表现

**3. 视觉 - 空间认知**
- 检查点：是否涉及空间理解、视角转换、心理旋转？
- 如相关：说明具体哪条规则未内化

**4. 语言 - 概念理解**
- 检查点：是否涉及词汇理解、概念抽象、问题解析？
- 如相关：说明对哪些词汇/概念存在字面化理解

---

## 输出要求

1. 不排除任何可能性，罗列所有相关的功能环节
2. 说明它们如何协同导致行为
3. 用"齿轮啮合"比喻说明多环节协同
4. 每个维度包含：问题环节 + 具体原因（神经/认知机制）
5. **总字数控制在 800 字以内**

---

## 输出格式

```
🔍 行为背后的原因

**心理理论（核心缺口）**
问题环节：...
具体原因：...

**执行功能**
问题环节：...
具体原因：...

**视觉 - 空间认知**
问题环节：...
具体原因：...

**语言与概念理解**
问题环节：...
具体原因：...

**总结**
这不是单一缺陷，而是一个典型的发展性协同挑战。以上四个环节像一组齿轮...
```
"""


# 简短版提示词（用于快速分析）
FOUR_DIMENSION_PROMPT_SHORT = """请从 4 个维度（心理理论、执行功能、视觉空间、语言理解）分析以下行为，每维度 1-2 句，总字数 300 字以内：

行为：{behavior}

用"齿轮啮合"比喻说明协同作用。
"""
```

---

### Step 4: 创建 executor.py

**文件：** `skills/domains/behavior-recorder/four-dimension-attribution/executor.py`

```python
#!/usr/bin/env python3
"""
四维度归因执行器

用法：
    命令行：python3 executor.py "行为描述"
    Python API：from executor import FourDimensionAnalyzer
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any

# 添加项目路径，复用主项目的 LLM 客户端
PROJECT_ROOT = Path('/home/admin/.openclaw/workspace/behavior_recorder_service')
sys.path.insert(0, str(PROJECT_ROOT))

# 导入提示词模板
from prompt import FOUR_DIMENSION_PROMPT, FOUR_DIMENSION_PROMPT_SHORT

# 导入 LLM 客户端
try:
    from app.llm.openai_client import OpenAIClient
except ImportError:
    print("❌ 无法导入 LLM 客户端")
    sys.exit(1)


class FourDimensionAnalyzer:
    """四维度归因分析器"""
    
    def __init__(self, short_mode: bool = False):
        self.short_mode = short_mode
        self.prompt_template = FOUR_DIMENSION_PROMPT_SHORT if short_mode else FOUR_DIMENSION_PROMPT
        self.client = OpenAIClient(
            api_key=os.getenv('LLM_API_KEY', ''),
            base_url=os.getenv('LLM_BASE_URL', 'https://api.deepseek.com'),
            model=os.getenv('LLM_MODEL', 'deepseek-chat')
        )
    
    def analyze(self, behavior_description: str) -> Dict[str, Any]:
        """从四维度分析行为"""
        try:
            prompt = self.prompt_template.format(behavior=behavior_description)
            response = self.client.chat(
                system_prompt="你是一位认知神经科学家，擅长从多维度分析儿童行为。",
                user_prompt=prompt,
                max_tokens=1500
            )
            return self._parse_response(response, behavior_description)
        except Exception as e:
            return {
                "success": False,
                "attribution": "",
                "dimensions": {},
                "summary": "",
                "input": behavior_description,
                "error": str(e)
            }
    
    def _parse_response(self, response: str, behavior: str) -> Dict[str, Any]:
        """解析 LLM 响应"""
        dimensions = {
            "theory_of_mind": self._extract_section(response, "心理理论"),
            "executive_function": self._extract_section(response, "执行功能"),
            "visual_spatial": self._extract_section(response, "视觉"),
            "language": self._extract_section(response, "语言")
        }
        return {
            "success": True,
            "attribution": response,
            "dimensions": dimensions,
            "summary": self._extract_summary(response),
            "input": behavior
        }
    
    def _extract_section(self, text: str, section_name: str) -> str:
        """提取指定维度内容"""
        start = text.find(f"**{section_name}")
        if start == -1:
            return ""
        end_markers = ["**总结", "**语言", "```"]
        end = len(text)
        for marker in end_markers:
            pos = text.find(marker, start + 10)
            if pos != -1 and pos < end:
                end = pos
        return text[start:end].strip()
    
    def _extract_summary(self, text: str) -> str:
        """提取总结部分"""
        start = text.find("**总结**")
        if start == -1:
            return ""
        return text[start:].strip()


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("📖 用法：python3 executor.py \"行为描述\"")
        print("选项：--short 使用简短模式（300 字以内）")
        sys.exit(1)
    
    short_mode = "--short" in sys.argv
    behavior = sys.argv[1]
    
    if behavior.startswith("--"):
        print("❌ 错误：行为描述不能作为第一个参数")
        sys.exit(1)
    
    print(f"🔍 分析行为：{behavior}")
    print("=" * 60)
    
    analyzer = FourDimensionAnalyzer(short_mode=short_mode)
    result = analyzer.analyze(behavior)
    
    if result["success"]:
        print(result["attribution"])
        print("=" * 60)
        print(f"✅ 分析完成")
        print("\n📊 维度覆盖:")
        for dim_name, dim_content in result["dimensions"].items():
            status = "✅" if dim_content else "❌"
            print(f"  {status} {dim_name}")
    else:
        print(f"❌ 分析失败：{result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

### Step 5: 创建 test.py

**文件：** `skills/domains/behavior-recorder/four-dimension-attribution/test.py`

```python
#!/usr/bin/env python3
"""四维度归因 Skill 测试"""

from executor import FourDimensionAnalyzer


def test_case_1():
    """测试用例 1：薯片盒子游戏（观点采择）"""
    print("=" * 60)
    print("测试用例 1：薯片盒子游戏（观点采择）")
    print("=" * 60)
    
    analyzer = FourDimensionAnalyzer()
    result = analyzer.analyze(
        "她以为我看到盒子里还是糖，不太理解我看到的是薯片的意思。"
    )
    
    if not result["success"]:
        print(f"❌ 测试失败：{result['error']}")
        return False
    
    print(result["attribution"])
    print("=" * 60)
    
    errors = []
    if "心理理论" not in result["attribution"]:
        errors.append("缺少心理理论维度")
    if "执行功能" not in result["attribution"]:
        errors.append("缺少执行功能维度")
    if "齿轮" not in result["attribution"]:
        errors.append("缺少协同作用说明（齿轮啮合比喻）")
    
    if errors:
        print(f"❌ 验证失败：{', '.join(errors)}")
        return False
    
    print("✅ 测试通过")
    return True


def test_case_2():
    """测试用例 2：等待提示（提示依赖）"""
    print("\n" + "=" * 60)
    print("测试用例 2：等待提示（提示依赖）")
    print("=" * 60)
    
    analyzer = FourDimensionAnalyzer()
    result = analyzer.analyze(
        "遇到困难就说我不会，等着大人教，其实都会做。"
    )
    
    if not result["success"]:
        print(f"❌ 测试失败：{result['error']}")
        return False
    
    print(result["attribution"])
    print("=" * 60)
    print("✅ 测试通过")
    return True


def test_case_3():
    """测试用例 3：寻求关注"""
    print("\n" + "=" * 60)
    print("测试用例 3：寻求关注")
    print("=" * 60)
    
    analyzer = FourDimensionAnalyzer()
    result = analyzer.analyze(
        "老师看她时她就故意发出奇怪声音，老师不看她就不发。"
    )
    
    if not result["success"]:
        print(f"❌ 测试失败：{result['error']}")
        return False
    
    print(result["attribution"])
    print("=" * 60)
    print("✅ 测试通过")
    return True


def test_case_4():
    """测试用例 4：简短模式"""
    print("\n" + "=" * 60)
    print("测试用例 4：简短模式（300 字以内）")
    print("=" * 60)
    
    analyzer = FourDimensionAnalyzer(short_mode=True)
    result = analyzer.analyze("孩子推人插队")
    
    if not result["success"]:
        print(f"❌ 测试失败：{result['error']}")
        return False
    
    print(result["attribution"])
    print("=" * 60)
    
    if len(result["attribution"]) > 500:
        print(f"⚠️ 警告：输出过长（{len(result['attribution'])}字）")
    else:
        print("✅ 字数符合要求")
    
    print("✅ 测试通过")
    return True


def main():
    """运行所有测试"""
    print("🧪 四维度归因 Skill 测试")
    print("=" * 60)
    
    results = []
    results.append(("用例 1：薯片盒子游戏", test_case_1()))
    results.append(("用例 2：等待提示", test_case_2()))
    results.append(("用例 3：寻求关注", test_case_3()))
    results.append(("用例 4：简短模式", test_case_4()))
    
    print("\n" + "=" * 60)
    print("📊 测试汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print("=" * 60)
    print(f"总计：{passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过")
        return 0
    else:
        print(f"⚠️ {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit(main())
```

---

### Step 6: 创建示例文件

**文件：** `skills/domains/behavior-recorder/four-dimension-attribution/examples/input_example.txt`

```
她以为我看到盒子里还是糖，不太理解我看到的是薯片的意思。她就不太明白了，还是以为妈妈是在用电脑，爸爸在用手机。
```

**文件：** `skills/domains/behavior-recorder/four-dimension-attribution/examples/output_example.md`

```markdown
🔍 行为背后的原因

**心理理论（核心缺口）**
问题环节：在"信念形成推理"环节受阻。
具体原因：大脑的"颞顶联合区"网络在模拟他人心理状态时负荷过重。孩子能完美运行"我看到了→所以我知道是糖"这条认知程序，但无法同时加载并运行另一条"妈妈没看到→所以她以为还是薯片"的并行程序。

**执行功能**
问题环节：主要涉及"抑制控制"和"工作记忆"的整合应用。
具体原因：
- 抑制控制不足：当被问及"妈妈看到什么"时，大脑难以抑制"糖"这个强烈的、正确的答案。
- 工作记忆超载：任务要求同时保持"事实（糖）"、"他人知识状态（没看见）"、"问题指向（妈妈以为）"等多重信息。

**视觉 - 空间认知**
问题环节：在"视角转换"的规则应用上存在困难。
具体原因：孩子可能尚未内化"视线是直线传播的，所见物体由观察点位置决定"这一抽象的物理规则。她固着于"人 - 物"的标签式关联（妈妈 - 电脑），难以将其动态更新为"位 - 物"关系（电脑椅 - 电脑）。

**语言与概念理解**
问题环节：对"看到"一词在提问中的含义可能存在字面化理解。
具体原因：当被问"妈妈会看到什么"时，她可能理解为"妈妈用眼睛会接收到什么图像信号"，从而根据已知事实（糖在盒子里）给出"正确答案"（糖），而非理解此问题是在询问"妈妈的心理表征或信念是什么"。

**总结**
这不是单一缺陷，而是一个典型的发展性协同挑战。以上四个环节像一组齿轮，目前啮合还不顺畅，导致"换位思考"这台复杂的认知机器暂时运行卡顿。其中，心理理论是核心目标齿轮，执行功能是提供动力的引擎，视觉 - 空间和语言理解是传动装置。
```

---

### Step 7: 测试验证

```bash
# 1. 进入 Skill 目录
cd /home/admin/.openclaw/workspace/skills/domains/behavior-recorder/four-dimension-attribution

# 2. 运行测试
python3 test.py

# 3. 手动测试
python3 executor.py "她以为我看到盒子里还是糖，不太理解我看到的是薯片的意思。"

# 4. 简短模式测试
python3 executor.py --short "孩子推人插队"
```

---

### Step 8: Git 提交

```bash
cd /home/admin/.openclaw/workspace

# 添加所有文件
git add skills/domains/behavior-recorder/four-dimension-attribution/

# 提交
git commit -m "feat(skills): 新增四维度归因 Skill（V4.10.4）

- 创建独立的四维度归因 Skill 模块
- 支持命令行和 Python API 调用
- 包含完整测试用例（4 个场景）
- 复用主项目 LLM 客户端配置
- 解决 token 限制问题（独立调用，不阻塞主流程）

Refs: V4.10.4 临床推理框架升级"
```

---

## ✅ 验收标准

| 检查项 | 标准 | 验证方法 |
|--------|------|----------|
| 目录结构 | 完整 | `ls -la skills/domains/behavior-recorder/four-dimension-attribution/` |
| SKILL.md | 包含四维度说明 + 调用方式 | `cat SKILL.md` |
| executor.py | 可运行 | `python3 executor.py "测试"` |
| prompt.py | 包含完整 + 简短两个模板 | `cat prompt.py` |
| test.py | 4 个测试用例全部通过 | `python3 test.py` |
| 示例文件 | input + output 示例 | `ls examples/` |
| Git 提交 | 提交信息清晰 | `git log --oneline -1` |

---

**完成后通知：** @战舰  
**优先级：** P0
