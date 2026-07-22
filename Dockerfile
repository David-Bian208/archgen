# ArchGen Dockerfile — 多阶段构建
# 阶段 1: 构建前端
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --production=false 2>/dev/null || npm install
COPY frontend/ ./
RUN npm run build

# 阶段 2: 运行环境
FROM python:3.10-slim

LABEL maintainer="david"
LABEL description="ArchGen — AI 架构生成器"

WORKDIR /app

# 安装 playwright 依赖（用于截图服务）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Chromium
RUN playwright install chromium

# 复制前端构建产物
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 复制应用代码
COPY . .

# 创建运行时目录
RUN mkdir -p data logs output

# 暴露端口
EXPOSE 8972

# 启动
CMD ["python", "main.py"]
