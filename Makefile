# AI 协同开发环境 - Makefile
# 版本：V6.0.7
# 使用：make init / make sync / make clean

.PHONY: init sync clean help

# 默认目标
all: help

help:
	@echo " AI 协同开发环境 - 可用命令:"
	@echo ""
	@echo "  make init    - 初始化环境（安装依赖 + 注册技能）"
	@echo "  make sync    - 同步技能声明（重新加载）"
	@echo "  make clean   - 清理运行时缓存"
	@echo "  make help    - 显示帮助信息"
	@echo ""

# 初始化环境
init:
	@echo "🔧 初始化 AI 协同环境..."
	pip3 install -r requirements-ci.txt
	python3 .claw/skill_loader.py
	python3 .claw/skill_guard.py
	@echo "✅ 初始化完成。"
	@echo ""
	@echo "📝 下一步:"
	@echo "  1. 配置环境变量：export NOTIFY_WEBHOOK='你的 Webhook'"
	@echo "  2. 测试技能调用：python3 test_skill_trace.py"
	@echo "  3. 推送测试：git push origin main"

# 同步技能声明
sync:
	@echo "🔄 同步技能声明..."
	python3 .claw/skill_loader.py
	python3 .claw/skill_guard.py
	@echo "✅ 路由索引与熔断清单已更新。"

# 清理运行时缓存
clean:
	@echo "🧹 清理运行时缓存..."
	rm -rf .claw/generated/*
	rm -rf .claw/logs/*
	rm -f roi_report.md
	rm -f skill_alerts.md
	rm -f trea_report.json
	rm -f arch_report.json
	rm -f security_report.json
	@echo "✅ 缓存已清理。"
