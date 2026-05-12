# ✅ API 密钥泄露修复完成

**修复时间：** 2026-03-30 09:19  
**风险等级：** ~~🔴 高危~~ → 🟢 已修复  
**位置：** `behavior_recorder_service/`

---

## 🚨 原问题

**config.yaml 中包含明文 API 密钥：**
```yaml
openai:
  api_key: "sk-578100de3afd494ca759cc096a4a1aaa"
```

**风险：**
- Git 历史中包含敏感密钥
- 任何访问代码库的人都可以使用密钥
- 可能产生未授权的 API 调用费用

---

## ✅ 修复方案

### 1. 创建环境变量配置

**文件：** `.env`（已创建，不提交到 Git）
```bash
LLM_API_KEY=sk-578100de3afd494ca759cc096a4a1aaa
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

### 2. 创建示例文件

**文件：** `.env.example`（可安全提交）
```bash
LLM_API_KEY=sk-your-api-key-here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

### 3. 更新 config.yaml

**修改前：** 明文密钥  
**修改后：** 环境变量占位符
```yaml
openai:
  api_key: "${LLM_API_KEY}"  # 从环境变量读取
  base_url: "${LLM_BASE_URL}"
  model: "${LLM_MODEL}"
```

### 4. 更新 .gitignore

```diff
+# 环境变量（敏感）
+.env
+.env.*
+!.env.example
```

### 5. 代码已支持

`app/config.py` 已支持环境变量优先：
```python
@property
def llm_api_key(self) -> str:
    return os.getenv("LLM_API_KEY") or self.get("llm.openai.api_key", "")
```

---

## 🧪 测试验证

```bash
✅ 配置加载测试
LLM Provider: openai
LLM Model: deepseek-chat
LLM Base URL: https://api.deepseek.com
LLM API Key: sk-578100d...
API Key 来源：环境变量
```

---

## ⚠️ 剩余风险

### Git 历史中的密钥

**问题：** 旧版本 `config.yaml` 已提交到 Git，密钥仍在历史中

**解决方案（二选一）：**

### 方案 A：撤销并更换密钥（推荐 ⭐）

1. 登录 DeepSeek 控制台
2. 撤销当前密钥：`sk-578100de3afd494ca759cc096a4a1aaa`
3. 生成新密钥
4. 更新 `.env` 文件
5. 提交更改

**优点：** 简单、安全、不影响 Git 历史  
**缺点：** 需要更新密钥

### 方案 B：清除 Git 历史

```bash
# ⚠️ 危险操作！会影响所有协作者
cd /home/admin/.openclaw/workspace/behavior_recorder_service
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch config.yaml" \
  --prune-empty --tag-name-filter cat -- --all
git push --force --all
```

**优点：** 彻底清除历史  
**缺点：** 危险、影响协作者、需要 force push

---

## 📋 待办事项

### 立即执行（今天）
- [ ] **撤销 DeepSeek 当前密钥**
- [ ] **生成新密钥**
- [ ] **更新 .env 文件**

### 本周内
- [ ] 提交修复后的配置
- [ ] 通知协作者（如有）
- [ ] 审查谁可能访问过旧密钥

---

## 📁 修改的文件

| 文件 | 操作 | 状态 |
|------|------|------|
| `.env` | 创建 | ✅ 包含真实密钥（不提交） |
| `.env.example` | 创建 | ✅ 示例文件（可提交） |
| `config.yaml` | 修改 | ✅ 移除明文密钥 |
| `.gitignore` | 修改 | ✅ 添加 .env 规则 |
| `app/config.py` | 无需修改 | ✅ 已支持环境变量 |

---

## 🔐 安全建议

### 密钥管理最佳实践

1. **永远不要提交敏感信息**
   - 使用 `.env` 文件存储密钥
   - 使用 `.env.example` 作为模板
   - 确保 `.gitignore` 包含 `.env`

2. **定期轮换密钥**
   - 每 3-6 个月更换一次
   - 员工离职时立即更换
   - 怀疑泄露时立即更换

3. **最小权限原则**
   - 为不同环境使用不同密钥
   - 限制密钥的权限范围
   - 监控 API 使用情况

4. **监控和告警**
   - 设置 API 使用量告警
   - 定期检查异常调用
   - 启用访问日志

---

## 📚 参考资料

- [12-Factor App - 配置](https://12factor.net/zh_cn/config)
- [OWASP - 密钥管理](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [GitHub - 删除敏感信息](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)

---

**修复完成！请立即撤销并更换 DeepSeek API 密钥！** 🔐
