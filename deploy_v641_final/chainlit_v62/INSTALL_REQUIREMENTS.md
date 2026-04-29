# 战舰任务：Chainlit 安装需求

## 一、安装失败原因总结

### 失败操作
```bash
pip install chainlit
```

### 失败现象
- 命令执行后返回空输出
- 无任何安装进度提示
- 无任何错误信息
- Chainlit 最终未安装成功

### 推测原因
1. **网络问题**：容器环境可能无法访问 PyPI 官方源
2. **镜像源配置**：未配置国内 PyPI 镜像源（如清华源、阿里源）
3. **Python 环境问题**：容器内 Python/pip 环境可能缺少必要依赖

## 二、安装要求

### 优先方案：从 Git 安装（用户明确要求）
```bash
# 方案1：从 GitHub 源码安装
pip install git+https://github.com/Chainlit/chainlit.git

# 方案2：克隆后安装
git clone https://github.com/Chainlit/chainlit.git
cd chainlit
pip install -e .
```

### 备选方案：配置国内镜像源
```bash
# 使用清华源
pip install chainlit -i https://pypi.tuna.tsinghua.edu.cn/simple

# 使用阿里源
pip install chainlit -i https://mirrors.aliyun.com/pypi/simple/

# 使用中科大源
pip install chainlit -i https://pypi.mirrors.ustc.edu.cn/simple/
```

### 备选方案：指定版本安装
```bash
# 安装稳定版本
pip install chainlit==1.3.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 三、环境信息

- **操作系统**：Linux（容器环境）
- **项目路径**：`/home/admin/.openclaw/workspace/behavior_recorder_service`
- **Python 环境**：需要确认当前 Python 版本和 pip 版本
- **现有服务**：FastAPI 运行在端口 8001（V6.1.0）

## 四、安装后验证

```bash
# 验证安装成功
chainlit --version

# 测试启动
cd /home/admin/.openclaw/workspace/behavior_recorder_service/chainlit_v62
chainlit run app.py --port 8002
```

## 五、注意事项

1. **不要影响现有服务**：FastAPI 在 8001 端口运行，Chainlit 需使用其他端口（建议 8002）
2. **依赖冲突检查**：安装前检查现有 Python 包，避免依赖冲突
3. **安装后告知**：安装完成后告知小治，以便继续后续开发

## 六、备用方案

如果 Chainlit 安装持续失败，已准备 FastAPI SSE 实现方案：
- 文件位置：`/home/admin/.openclaw/workspace/behavior_recorder_service/chainlit_v62/app.py`
- 功能：提供 `/api/v6/stream` SSE 端点
- 前端对接方式：EventSource API

## 七、任务优先级

1. **最高优先级**：从 Git 源码安装 Chainlit
2. **次优先级**：配置国内镜像源安装
3. **保底方案**：使用已准备的 FastAPI SSE 方案
