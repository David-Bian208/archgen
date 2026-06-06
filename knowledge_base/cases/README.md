# 案例库结构

本目录存放 ArchGen 内容生成所需的案例素材。

## 目录结构

```
cases/
├── README.md          # 本文件
├── ai_efficiency/     # AI 效率工具案例
├── decision_thinking/ # 决策思维升级案例
├── personal_systems/  # 个人系统构建案例
├── ai_leadership/     # AI 赋能领导力案例
└── templates/         # 案例模板
```

## 案例模板

每个案例文件使用 Markdown 格式，包含 YAML front matter：

```markdown
---
title: "某科技公司用 Notion AI 节省 40% 会议时间"
category: "AI 效率工具"
industry: "科技/互联网"
company_size: "50-200 人"
pain_point: "会议效率低，信息不同步"
solution: "Notion AI + 项目管理模板"
result: "节省 40% 会议时间，信息同步率提升 60%"
source_tag: "user_input:case_001"
---

## 背景

（公司背景、面临的挑战）

## 实施过程

（具体步骤、工具选择、配置过程）

## 避坑指南

（遇到的问题、解决方案）

## ROI 测算

（投入产出比、时间节省、效率提升）

## 可复用性

（哪些做法可以推广到其他场景）
```

## 检索优先级

1. 本地案例库（当前目录）
2. AI-Pulse API
3. 用户手动补充

## source_tag 规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 用户输入 | `user_input:manual_编号` | `user_input:manual_001` |
| 本地知识库 | `local:文件名§节号` | `local:案例 001.md§避坑指南` |
| AI-Pulse | `ai_pulse:内容 ID` | `ai_pulse:12345` |
| AI 推断 | `ai_inferred:logic_chain` | `ai_inferred:llm_generated` |

## 渲染规则（P2 实施）

- 无 source_tag → 不渲染
- `ai_inferred` → "⚠️ [AI 推断] ..."
- 其他 → "[来源：xxx] ..."

## P0 阶段策略

当前所有 AI 生成内容打 `ai_inferred` 标签，渲染时暂不强制检查 source_tag。
