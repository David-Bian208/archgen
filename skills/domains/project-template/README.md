# 新项目技能包模板

**用途：** 快速创建新项目的领域技能包

---

## 📁 目录结构

```
domains/[project-name]/
├── skill-1/
│   ├── SKILL.md
│   └── executor.py
├── skill-2/
│   ├── SKILL.md
│   └── executor.py
└── README.md
```

---

## 🚀 创建步骤

### 1. 复制模板

```bash
cd /home/admin/.openclaw/workspace/skills/domains
cp -r project-template new-project
```

### 2. 创建技能目录

```bash
cd new-project
mkdir skill-name
```

### 3. 创建 SKILL.md

```markdown
# skill-name Skill

**领域技能 - [项目名称] 专用**

## 🎯 用途

[技能用途]

## 🎤 唤醒词

- `唤醒词 1` - 功能描述
- `唤醒词 2` - 功能描述

## 📝 输出格式

[输出格式示例]

**版本：** V1.0  
**类型：** 领域技能（[项目名称]）
```

### 4. 创建 executor.py

```python
"""
skill-name Skill 执行器
"""

def execute(command: str) -> str:
    """执行命令"""
    # 实现逻辑
    return "结果"

if __name__ == "__main__":
    import sys
    command = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("输入命令：")
    print(execute(command))
```

### 5. 测试加载

```bash
cd /home/admin/.openclaw/workspace/skills
python3 loader.py load -p new-project
```

---

## 📋 SKILL.md 模板

```markdown
# [skill-name] Skill

**领域技能 - [项目名称] 专用**

---

## 🎯 用途

[技能用途描述]

---

## 🎤 唤醒词（X 个）

### 分类 1
- `唤醒词` - 功能描述

### 分类 2
- `唤醒词` - 功能描述

---

## 📝 输出格式

### 场景 1

```
输出格式示例
```

### 场景 2

```
输出格式示例
```

---

## 🔧 技术实现

[技术实现说明]

---

## 📚 相关文档

| 文档 | 位置 |
|------|------|
| 文档 1 | 路径 |

---

**版本：** V1.0  
**类型：** 领域技能（[项目名称]）
```

---

## 📋 executor.py 模板

```python
"""
[skill-name] Skill 执行器

[技能描述]
"""

def execute(command: str) -> str:
    """
    执行命令
    
    Args:
        command: 自然语言命令
        
    Returns:
        执行结果
    """
    cmd = command.lower()
    
    # 命令解析
    if "关键词" in cmd:
        return "执行结果"
    
    # 默认帮助
    return """
[技能名称]

**可用命令：**
- 命令 1
- 命令 2

**示例：**
- 示例 1
- 示例 2
"""


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        command = input("输入命令：")
    
    print(execute(command))
```

---

## ✅ 检查清单

创建新技能包后检查：

- [ ] SKILL.md 包含用途、唤醒词、输出格式
- [ ] executor.py 实现命令解析
- [ ] 测试加载：`python3 loader.py load -p [project]`
- [ ] 测试执行：`python3 executor.py "唤醒词"`
- [ ] 更新 README.md

---

**版本：** V1.0  
**维护人：** 战舰 🛳️
