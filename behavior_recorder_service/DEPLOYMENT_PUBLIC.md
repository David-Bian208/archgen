# 公网部署方案 - Behavior Recorder Service

**创建时间:** 2026-03-19 18:55 GMT+8  
**当前版本:** V4.10.3  
**公网 IP:** 47.103.229.125

---

## 📋 部署前检查清单

### 1. 安全配置（⚠️ 必须完成）

- [ ] **修改默认 API 密钥** - 当前 config.yaml 使用测试密钥
- [ ] **配置防火墙** - 仅开放必要端口（80/443）
- [ ] **启用 HTTPS** - 使用 Let's Encrypt 免费证书
- [ ] **限制 CORS** - 从 `*` 改为具体域名
- [ ] **添加认证中间件** - 防止未授权访问

### 2. 域名与 DNS

- [ ] **购买域名** (可选但推荐)
- [ ] **配置 DNS A 记录** → 47.103.229.125
- [ ] **配置 DNS AAAA 记录** (如支持 IPv6)

### 3. 服务加固

- [ ] **使用 systemd 管理** - 替代直接运行 python3 main.py
- [ ] **配置日志轮转** - 防止日志占满磁盘
- [ ] **设置资源限制** - CPU/内存上限
- [ ] **启用健康检查** - 自动重启故障服务

---

## 🚀 部署方案选择

### 方案 A: Nginx 反向代理（推荐）⭐

**优点:**
- 支持 HTTPS/TLS 终止
- 负载均衡能力
- 静态文件缓存
- 请求限流/防 DDoS

**架构:**
```
用户 → Nginx(80/443) → 后端 (8000)
              ↓
         前端静态文件
```

### 方案 B: Docker Compose 部署

**优点:**
- 环境隔离
- 一键部署
- 易于回滚

**架构:**
```
用户 → Nginx → Docker(backend:8000, frontend:3000)
```

### 方案 C: 直接暴露（❌ 不推荐）

**仅用于测试，生产环境禁止使用**

---

## 🔧 方案 A 实施步骤（推荐）

### 步骤 1: 安装 Nginx

```bash
sudo apt update
sudo apt install -y nginx
```

### 步骤 2: 配置 Nginx

创建 `/etc/nginx/sites-available/behavior-recorder`:

```nginx
server {
    listen 80;
    server_name 47.103.229.125;  # 替换为您的域名
    
    # 前端静态文件
    location / {
        root /home/admin/.openclaw/workspace/behavior_recorder_service/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
    
    # 后端 API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

启用配置:
```bash
sudo ln -s /etc/nginx/sites-available/behavior-recorder /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 步骤 3: 配置 HTTPS（Let's Encrypt）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 步骤 4: 配置 systemd 服务

创建 `/etc/systemd/system/behavior-recorder.service`:

```ini
[Unit]
Description=Behavior Recorder Service
After=network.target

[Service]
Type=simple
User=admin
WorkingDirectory=/home/admin/.openclaw/workspace/behavior_recorder_service
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

# 资源限制
LimitNOFILE=65535
MemoryMax=1G
CPUQuota=80%

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=behavior-recorder

[Install]
WantedBy=multi-user.target
```

启用服务:
```bash
sudo systemctl daemon-reload
sudo systemctl enable behavior-recorder
sudo systemctl start behavior-recorder
sudo systemctl status behavior-recorder
```

### 步骤 5: 配置日志轮转

创建 `/etc/logrotate.d/behavior-recorder`:

```
/var/log/journal/*/behavior-recorder*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 admin admin
}
```

### 步骤 6: 安全加固

#### 6.1 修改 config.yaml

```yaml
server:
  host: "127.0.0.1"  # 仅监听本地
  port: 8000
  debug: false
```

#### 6.2 更新 CORS 配置

编辑 `main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # 改为具体域名
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "Authorization"],
)
```

#### 6.3 配置防火墙

```bash
# 如果使用 ufw
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw enable

# 如果使用 firewall-cmd
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload
```

---

## 📊 部署后验证

### 1. 服务状态检查

```bash
# Nginx 状态
sudo systemctl status nginx

# 后端服务状态
sudo systemctl status behavior-recorder

# 端口监听
ss -tlnp | grep -E "80|443|8000"
```

### 2. 健康检查

```bash
# 本地访问
curl http://localhost:8000/api/health

# 公网访问
curl http://47.103.229.125/api/health

# HTTPS 访问（配置证书后）
curl https://your-domain.com/api/health
```

### 3. 端到端测试

```bash
# 测试前端
curl -I http://47.103.229.125/

# 测试 API
curl -X POST http://47.103.229.125/api/v3/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": null, "user_input": "测试"}'
```

---

## 🔒 安全最佳实践

### 必须执行

1. **更换 API 密钥** - 不要使用示例密钥
2. **启用 HTTPS** - 防止中间人攻击
3. **限制 CORS** - 仅允许信任域名
4. **配置防火墙** - 最小权限原则
5. **定期更新** - 保持系统和依赖最新

### 建议执行

1. **添加 API 认证** - JWT 或 API Key
2. **配置速率限制** - 防止滥用
3. **启用访问日志** - 安全审计
4. **设置监控告警** - 异常检测
5. **定期备份** - 数据/配置备份

---

## 📈 监控与运维

### 监控指标

- **服务可用性** - 健康检查成功率 > 99%
- **响应时间** - P95 < 2s
- **错误率** - 5xx 错误 < 0.1%
- **资源使用** - CPU < 80%, 内存 < 80%

### 日志位置

- **Nginx 访问日志:** `/var/log/nginx/access.log`
- **Nginx 错误日志:** `/var/log/nginx/error.log`
- **应用日志:** `journalctl -u behavior-recorder`

### 告警配置（可选）

使用 Prometheus + Grafana 或云监控服务

---

## 🆘 故障排查

### 问题 1: Nginx 502 Bad Gateway

```bash
# 检查后端服务
sudo systemctl status behavior-recorder

# 检查端口
ss -tlnp | grep 8000

# 查看日志
journalctl -u behavior-recorder -n 50
```

### 问题 2: HTTPS 证书问题

```bash
# 检查证书状态
sudo certbot certificates

# 续期证书
sudo certbot renew
```

### 问题 3: CORS 错误

检查 `main.py` 中的 `allow_origins` 配置是否包含当前域名

---

## 📞 下一步行动

1. **确认部署方案** - 选择方案 A/B
2. **准备域名** (可选)
3. **执行安全加固** - 按清单逐项完成
4. **部署验证** - 完成端到端测试
5. **监控配置** - 设置基础监控

---

**当前状态:** 等待用户确认部署方案  
**负责人:** OpenClaw 部署工程师  
**联系方式:** 通过 workspace 文件更新进度
