# 行为记录员 Agent V3.9.1 Final - 还原指令

**备份日期**: 2026-03-07 00:16  
**备份版本**: V3.9.1 Final 稳定版  
**备份文件**: `behavior_recorder_service_V3.9.1_Final_20260307_001653.tar.gz`  
**备份大小**: 28MB

---

## 还原指令

**当需要还原到 V3.9.1 Final 稳定版时，请发送以下任一指令：**

### 指令格式

```
还原行为记录员到 V3.9.1 Final 版本
```

或

```
restore behavior recorder to V3.9.1 Final
```

或

```
恢复备份 V3.9.1
```

---

## 自动还原流程

收到还原指令后，系统将自动执行以下步骤：

### 1. 停止当前服务
```bash
cd /home/admin/.openclaw/workspace/behavior_recorder_service
./stop.sh
```

### 2. 备份当前状态（可选，防止误操作）
```bash
cd /home/admin/.openclaw/workspace
tar -czvf behavior_recorder_service_CURRENT_$(date +%Y%m%d_%H%M%S).tar.gz behavior_recorder_service/
```

### 3. 清理现有文件
```bash
cd /home/admin/.openclaw/workspace
rm -rf behavior_recorder_service
```

### 4. 解压备份文件
```bash
cd /home/admin/.openclaw/workspace
tar -xzf behavior_recorder_service_V3.9.1_Final_20260307_001653.tar.gz
```

### 5. 恢复服务
```bash
cd /home/admin/.openclaw/workspace/behavior_recorder_service
./start-daemon.sh
```

### 6. 验证还原
```bash
./test_final.sh
```

---

## 手动还原步骤

如果需要手动还原，请按顺序执行以下命令：

```bash
# 1. 停止服务
cd /home/admin/.openclaw/workspace/behavior_recorder_service
./stop.sh

# 2. 返回 workspace 目录
cd /home/admin/.openclaw/workspace

# 3. 重命名当前目录（保留备份）
mv behavior_recorder_service behavior_recorder_service_backup_$(date +%Y%m%d_%H%M%S)

# 4. 解压 V3.9.1 Final 备份
tar -xzf behavior_recorder_service_V3.9.1_Final_20260307_001653.tar.gz

# 5. 启动服务
cd behavior_recorder_service
./start-daemon.sh

# 6. 验证版本
curl http://localhost:8000/docs | grep "V3.9.1"
```

---

## 备份文件信息

| 属性 | 值 |
|------|-----|
| **文件名** | `behavior_recorder_service_V3.9.1_Final_20260307_001653.tar.gz` |
| **版本** | V3.9.1 Final 稳定版 |
| **备份日期** | 2026-03-07 00:16:53 |
| **文件大小** | 28MB |
| **包含内容** | 完整源代码、配置文件、文档、测试脚本 |
| **排除内容** | node_modules、日志文件、PID 文件 |

---

## 还原后验证

还原完成后，请确认以下项目：

### 1. 检查版本号
```bash
curl http://localhost:8000/docs | grep "V3.9.1"
# 应输出：记录观察助手 V3.9.1 Final
```

### 2. 检查前端
```bash
curl http://localhost:3000 | grep "V3.9.1"
# 应包含：V3.9.1 Final
```

### 3. 运行测试脚本
```bash
cd /home/admin/.openclaw/workspace/behavior_recorder_service
./test_final.sh
# 所有测试项应显示 ✅
```

### 4. 功能测试
访问 http://localhost:3000，完成一次完整对话流程，确认：
- ✅ 无乱码
- ✅ 文案精炼
- ✅ 流程稳定

---

## 注意事项

1. **还原前建议**：
   - 停止当前运行的服务
   - 如有重要数据，先单独备份

2. **还原后检查**：
   - 确认服务正常启动
   - 验证版本号正确
   - 测试基本功能

3. **备份保留**：
   - 原始备份文件请妥善保留
   - 建议至少保留 30 天

4. **版本锁定**：
   - V3.9.1 Final 是稳定版
   - 还原后不应再进行功能性修改

---

## 快速参考

**还原指令**（任一即可）:
- `还原行为记录员到 V3.9.1 Final 版本`
- `restore behavior recorder to V3.9.1 Final`
- `恢复备份 V3.9.1`

**备份文件位置**:
```
/home/admin/.openclaw/workspace/behavior_recorder_service_V3.9.1_Final_20260307_001653.tar.gz
```

**服务启动命令**:
```bash
cd /home/admin/.openclaw/workspace/behavior_recorder_service
./start-daemon.sh
```

**服务停止命令**:
```bash
cd /home/admin/.openclaw/workspace/behavior_recorder_service
./stop.sh
```

---

**文档创建时间**: 2026-03-07 00:17  
**适用版本**: V3.9.1 Final 稳定版  
**状态**: ✅ 可用
