# 排布 (PaiBu) Dockerfile — 多阶段构建
FROM python:3.10-slim

LABEL maintainer="david"
LABEL description="排布 PaiBu — 海报生成服务"

WORKDIR /app

# 安装 playwright 依赖
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

# 复制应用代码
COPY . .

# 创建运行时目录
RUN mkdir -p output logs

# 暴露端口
EXPOSE 8090

# 启动
CMD ["python", "main.py"]
