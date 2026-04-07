# 🔴 P0 安全警告 - API 密钥泄露

**发现时间：** 2026-03-30 09:15  
**风险等级：** 🔴 高危  
**位置：** `behavior_recorder_service/config.yaml`

---

## 🚨 问题描述

**config.yaml 中包含明文 API 密钥：**

```yaml
openai:
  api_key: "sk-578100de3afd494ca759cc096a4a1aaa"
```

---

## ⚠️ 风险

1. **密钥泄露** - 任何访问该文件的人都可以使用你的 API 密钥
2. **滥用风险** - 可能导致 API 额度被盗用
3. **代码库泄露** - 如果提交到 Git，密钥将永久泄露
4. **财务风险** - 可能产生未授权的 API 调用费用

---

## ✅ 立即修复

### 1. 立即撤销当前密钥

登录 DeepSeek 控制台，撤销密钥：`sk-578100de3afd494ca759cc096a4a1aaa`

### 2. 使用环境变量

**修改 config.yaml：**
```yaml
llm:
  provider: "openai"
  openai:
    api_key: "${DEEPSEEK_API_KEY}"  # 使用环境变量
    base_url: "https://api.deepseek.com"
    model: "deepseek-chat"
```

**创建 .env 文件：**
```bash
# behavior_recorder_service/.env
DEEPSEEK_API_KEY=sk-your-new-key-here
```

### 3. 更新 .gitignore

确保 `.env` 文件不被提交：
```bash
# .gitignore
.env
.env.*
!env.example
```

**创建 .env.example（不含真实密钥）：**
```bash
# .env.example
DEEPSEEK_API_KEY=your-api-key-here
```

### 4. 修改代码读取环境变量

**main.py 或配置加载处：**
```python
import os
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件

api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise ValueError("DEEPSEEK_API_KEY not set")
```

---

## 📋 安全配置检查清单

```
[ ] 撤销泄露的 API 密钥
[ ] 生成新密钥
[ ] 使用环境变量存储密钥
[ ] 更新 .gitignore
[ ] 创建 .env.example
[ ] 修改代码读取环境变量
[ ] 从 Git 历史中清除旧密钥（如已提交）
[ ] 审查谁可能访问过旧密钥
```

---

## 🔍 其他潜在风险

### 检查 Git 历史

```bash
# 检查 config.yaml 是否已提交
git log --oneline -- behavior_recorder_service/config.yaml

# 如果已提交，需要清除历史
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch behavior_recorder_service/config.yaml" \
  --prune-empty --tag-name-filter cat -- --all
```

### 检查是否有其他敏感文件

```bash
# 查找可能的密钥文件
grep -rn "sk-" /home/admin/.openclaw/workspace/behavior_recorder_service/ --include="*.yaml" --include="*.yml" --include="*.json"
```

---

## 📚 参考资料

- [12-Factor App - 配置](https://12factor.net/zh_cn/config)
- [OWASP - 密钥管理](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)

---

**建议立即执行修复！**
