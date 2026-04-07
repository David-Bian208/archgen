# Skills 索引 - 三方协作技能库

**版本：** V1.0  
**创建日期：** 2026-04-02  
**用途：** 快速查找和调用技能，支持语义检索

**参考：** 复旦 DataHub Skills 平台（140 万 + Skills，6 大维度 30 项指标）

---

## 📊 技能评估体系

**评分标准（6 大维度）：**
| 维度 | 说明 | 权重 |
|------|------|------|
| **质量** | 技能完成度、文档完整性 | 25% |
| **安全** | 隐私泄露风险、临床合规性 | 25% |
| **兼容性** | 与现有技能是否冲突 | 15% |
| **实用性** | 使用频率、解决问题能力 | 20% |
| **可维护性** | 更新频率、文档清晰度 | 10% |
| **创新性** | 独特性、领先性 | 5% |

**综合评分：**
- ⭐⭐⭐⭐⭐ 5/5 - 核心技能，必须加载
- ⭐⭐⭐⭐ 4/5 - 重要技能，按场景加载
- ⭐⭐⭐ 3/5 - 辅助技能，按需加载
- ⭐⭐ 2/5 - 边缘技能，不推荐
- ⭐ 1/5 - 已废弃，不要使用

---

## 🎯 核心技能（⭐⭐⭐⭐⭐ 5/5）

### 1. 三方协作
**路径：** `skills/三方协作/SKILL.md`  
**评分：** ⭐⭐⭐⭐⭐ 5/5  
**安全评估：** ✅ 通过（无隐私泄露风险）  
**兼容性：** ✅ 与所有技能兼容  
**更新时间：** 2026-04-02  

**用途：** 定义 DAVID+ 战舰+trae 的协作流程、角色分工、禁令清单

**适用场景：**
- 所有协作任务
- 任务派发
- 代码审查
- 部署确认

**技能组合：**
- + flow-master → 完整流程控制
- + test-master → 测试验证流程
- + security-auditor → 安全审查流程

---

## 🔧 开发技能（⭐⭐⭐⭐ 4/5）

### 2. flow-master
**路径：** `skills/flow-master/SKILL.md`  
**评分：** ⭐⭐⭐⭐ 4/5  
**安全评估：** ✅ 通过  
**兼容性：** ✅ 与三方协作兼容  
**更新时间：** 2026-04-01  

**用途：** 流程控制、任务管理、状态跟踪

**适用场景：**
- 复杂任务拆分
- 多步骤流程
- 状态管理

---

### 3. test-master
**路径：** `skills/test-master/SKILL.md`  
**评分：** ⭐⭐⭐⭐ 4/5  
**安全评估：** ✅ 通过  
**兼容性：** ✅ 与所有测试工具兼容  
**更新时间：** 2026-04-01  

**用途：** 测试用例设计、测试执行、覆盖率审计

**适用场景：**
- 单元测试
- 集成测试
- 回归测试
- 覆盖率审计

**技能组合：**
- + 三方协作 → 完整测试流程（小测试角色）

---

## 🛡️ 安全技能（⭐⭐⭐⭐ 4/5）

### 4. security-auditor
**路径：** `skills/security-auditor/SKILL.md`  
**评分：** ⭐⭐⭐⭐ 4/5  
**安全评估：** ✅ 通过（本身就是安全审计）  
**兼容性：** ✅ 与所有代码审查兼容  
**更新时间：** 2026-04-01  

**用途：** 代码安全审计、OWASP Top 10 检查、敏感信息检测

**适用场景：**
- 代码审查
- 安全漏洞扫描
- API Key 检测
- SQL 注入/XSS 防护

**技能组合：**
- + 三方协作 → 完整代码审查流程

---

## 📦 通用技能（⭐⭐⭐ 3/5）

### 5. FastAPI
**路径：** `skills/fastapi/SKILL.md`  
**评分：** ⭐⭐⭐ 3/5  
**安全评估：** ⚠️ 需要注意 API Key 管理  
**兼容性：** ✅ 与 Python 项目兼容  
**更新时间：** 2026-04-01  

**用途：** FastAPI 开发、类型提示、验证、异步支持

**适用场景：**
- Python API 开发
- 快速原型

---

### 6. qwen-image
**路径：** `skills/qwen-image/SKILL.md`  
**评分：** ⭐⭐⭐ 3/5  
**安全评估：** ✅ 通过  
**兼容性：** ✅ 独立技能  
**更新时间：** 2026-04-01  

**用途：** 使用 Qwen Image API 生成图片

**适用场景：**
- 图片生成
- 视觉内容创作

---

### 7. stock-watcher
**路径：** `skills/stock-watcher/SKILL.md`  
**评分：** ⭐⭐⭐ 3/5  
**安全评估：** ✅ 通过  
**兼容性：** ✅ 独立技能  
**更新时间：** 2026-04-01  

**用途：** 股票 watchlist 管理、性能总结

**适用场景：**
- 股票跟踪
- 投资分析

---

## 🎭 领域技能（⭐⭐⭐ 3/5）

### 8. otaku-reco
**路径：** `skills/otaku-reco/SKILL.md`  
**评分：** ⭐⭐⭐ 3/5  
**安全评估：** ✅ 通过  
**兼容性：** ✅ 独立技能  
**更新时间：** 2026-04-01  

**用途：** 二次元鉴赏/推荐（基于 AniList）

**适用场景：**
- 番剧推荐
- 角色推荐

---

### 9. otaku-wiki
**路径：** `skills/otaku-wiki/SKILL.md`  
**评分：** ⭐⭐⭐ 3/5  
**安全评估：** ✅ 通过  
**兼容性：** ✅ 独立技能  
**更新时间：** 2026-04-01  

**用途：** 番剧/角色百科问答（AniList API）

**适用场景：**
- 查番
- 查角色
- 查声优

---

## 📚 文档技能（⭐⭐⭐ 3/5）

### 10. feishu-doc
**路径：** `/home/admin/.openclaw/extensions/feishu/skills/feishu-doc/SKILL.md`  
**评分：** ⭐⭐⭐ 3/5  
**安全评估：** ⚠️ 需要 Feishu API 权限  
**兼容性：** ✅ 与 Feishu 集成兼容  
**更新时间：** 2026-04-01  

**用途：** Feishu 文档读写操作

**适用场景：**
- 云文档管理
- docx 链接处理

---

### 11. feishu-drive
**路径：** `/home/admin/.openclaw/extensions/feishu/skills/feishu-drive/SKILL.md`  
**评分：** ⭐⭐⭐ 3/5  
**安全评估：** ⚠️ 需要 Feishu API 权限  
**兼容性：** ✅ 与 Feishu 集成兼容  
**更新时间：** 2026-04-01  

**用途：** Feishu 云存储文件管理

**适用场景：**
- 云空间管理
- 文件夹操作

---

### 12. feishu-perm
**路径：** `/home/admin/.openclaw/extensions/feishu/skills/feishu-perm/SKILL.md`  
**评分：** ⭐⭐⭐ 3/5  
**安全评估：** ⚠️ 需要 Feishu API 权限  
**兼容性：** ✅ 与 Feishu 集成兼容  
**更新时间：** 2026-04-01  

**用途：** Feishu 权限管理

**适用场景：**
- 文档共享
- 协作管理

---

### 13. feishu-wiki
**路径：** `/home/admin/.openclaw/extensions/feishu/skills/feishu-wiki/SKILL.md`  
**评分：** ⭐⭐⭐ 3/5  
**安全评估：** ⚠️ 需要 Feishu API 权限  
**兼容性：** ✅ 与 Feishu 集成兼容  
**更新时间：** 2026-04-01  

**用途：** Feishu 知识库导航

**适用场景：**
- 知识库查询
- wiki 链接处理

---

## 🛠️ 工具技能（⭐⭐⭐ 3/5）

### 14. bluebubbles
**路径：** `/home/admin/.npm-global/lib/node_modules/openclaw/skills/bluebubbles/SKILL.md`  
**评分：** ⭐⭐⭐ 3/5  
**安全评估：** ⚠️ 需要 BlueBubbles API  
**兼容性：** ✅ 与 iMessage 集成  
**更新时间：** 2026-04-01  

**用途：** BlueBubbles 消息插件

**适用场景：**
- iMessage 收发
-  webhook 配置

---

### 15. clawhub
**路径：** `/home/admin/.npm-global/lib/node_modules/openclaw/skills/clawhub/SKILL.md`  
**评分：** ⭐⭐⭐ 3/5  
**安全评估：** ✅ 通过  
**兼容性：** ✅ 与 npm 兼容  
**更新时间：** 2026-04-01  

**用途：** ClawHub CLI 技能管理

**适用场景：**
- 技能搜索
- 技能安装/更新
- 技能发布

---

### 16. skill-creator
**路径：** `/home/admin/.npm-global/lib/node_modules/openclaw/skills/skill-creator/SKILL.md`  
**评分：** ⭐⭐⭐⭐ 4/5  
**安全评估：** ✅ 通过  
**兼容性：** ✅ 与所有技能兼容  
**更新时间：** 2026-04-01  

**用途：** 创建或更新 AgentSkills

**适用场景：**
- 技能设计
- 技能打包

---

### 17. tmux
**路径：** `/home/admin/.npm-global/lib/node_modules/openclaw/skills/tmux/SKILL.md`  
**评分：** ⭐⭐⭐ 3/5  
**安全评估：** ✅ 通过  
**兼容性：** ✅ 与远程服务器兼容  
**更新时间：** 2026-04-01  

**用途:** 远程 tmux 会话控制

**适用场景：**
- 远程 CLI
- 交互式会话

---

### 18. video-frames
**路径：** `/home/admin/.npm-global/lib/node_modules/openclaw/skills/video-frames/SKILL.md`  
**评分：** ⭐⭐⭐ 3/5  
**安全评估：** ✅ 通过  
**兼容性：** ✅ 需要 ffmpeg  
**更新时间：** 2026-04-01  

**用途：** 视频帧提取

**适用场景：**
- 视频处理
- 帧提取

---

### 19. weather
**路径：** `/home/admin/.npm-global/lib/node_modules/openclaw/skills/weather/SKILL.md`  
**评分：** ⭐⭐⭐ 3/5  
**安全评估：** ✅ 通过  
**兼容性：** ✅ 独立技能  
**更新时间：** 2026-04-01  

**用途：** 天气查询（无需 API key）

**适用场景：**
- 当前天气
- 天气预报

---

### 20. hn
**路径：** `/home/admin/.openclaw/skills/hn/hn/SKILL.md`  
**评分：** ⭐⭐⭐ 3/5  
**安全评估：** ✅ 通过  
**兼容性：** ✅ 独立技能  
**更新时间：** 2026-04-01  

**用途：** Hacker News 浏览

**适用场景：**
- 热门故事
- 评论查看

---

### 21. pptx-creator
**路径：** `/home/admin/.openclaw/skills/pptx-creator/pptx-creator/SKILL.md`  
**评分：** ⭐⭐⭐ 3/5  
**安全评估：** ✅ 通过  
**兼容性：** ✅ 独立技能  
**更新时间：** 2026-04-01  

**用途：** PPT 创建

**适用场景：**
- 幻灯片制作
- 报告生成

---

### 22. url-digest
**路径：** `/home/admin/.openclaw/skills/url-digest/url-digest/SKILL.md`  
**评分：** ⭐⭐⭐⭐ 4/5  
**安全评估：** ✅ 通过  
**兼容性：** ✅ 与 web_fetch 兼容  
**更新时间：** 2026-04-01  

**用途：** URL 内容提取和结构化

**适用场景：**
- 文章摘要
- 关键信息提取

---

## 📊 技能组合模板

### 组合 1：完整开发流程
```
1. 三方协作（任务派发）
2. flow-master（流程控制）
3. FastAPI（API 开发）
4. security-auditor（安全审查）
5. test-master（测试验证）
```

### 组合 2：代码审查流程
```
1. 三方协作（审查流程）
2. security-auditor（安全审计）
3. test-master（测试覆盖）
```

### 组合 3：新技能开发
```
1. skill-creator（技能设计）
2. 三方协作（协作规范）
3. test-master（测试覆盖）
4. clawhub（技能发布）
```

### 组合 4：Feishu 集成
```
1. feishu-doc（文档读写）
2. feishu-drive（文件管理）
3. feishu-perm（权限管理）
4. feishu-wiki（知识库）
```

---

## 🔍 语义检索指南

**按场景查找技能：**
- **协作场景** → 三方协作 + flow-master
- **开发场景** → FastAPI + security-auditor + test-master
- **安全场景** → security-auditor
- **测试场景** → test-master
- **Feishu 场景** → feishu-* 系列
- **外部工具** → bluebubbles + tmux

**按评分查找技能：**
- ⭐⭐⭐⭐⭐ 5/5 → 核心技能（必须加载）
- ⭐⭐⭐⭐ 4/5 → 重要技能（按场景加载）
- ⭐⭐⭐ 3/5 → 辅助技能（按需加载）

---

## 📈 技能统计

| 分类 | 数量 | 平均评分 |
|------|------|---------|
| 核心技能 | 1 | 5.0 |
| 开发技能 | 2 | 4.0 |
| 安全技能 | 1 | 4.0 |
| 通用技能 | 3 | 3.0 |
| 领域技能 | 2 | 3.0 |
| 文档技能 | 4 | 3.0 |
| 工具技能 | 9 | 3.1 |
| **总计** | **22** | **3.5** |

---

## 🔄 更新记录

| 日期 | 更新内容 | 更新人 |
|------|---------|--------|
| 2026-04-02 | 创建索引，添加评分体系 | 战舰 🛳️ |
| 2026-04-02 | 参考复旦 DataHub Skills 平台 | 战舰 🛳️ |

---

## 📞 外部资源

**复旦 DataHub Skills 平台**
- 访问：http://www.fudankw.cn:18000/search-skills.html
- 规模：140 万 + Skills
- 特色：6 大维度 30 项指标评估体系
- 启发：技能评分、安全评估、语义检索

**ClawHub**
- 访问：https://clawhub.com
- 用途：技能搜索、安装、发布
- CLI：`clawhub search/install/update`

---

**维护人：** 战舰 🛳️  
**更新频率：** 每次新增/修改技能后立即更新  
**下次更新：** 新增技能时

**所有技能调用前，请先查阅此索引！**
