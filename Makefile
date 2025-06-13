# NexusMind 项目管理 Makefile

.PHONY: help install test start stop clean infrastructure status

# 默认目标
help:
	@echo "🧠 NexusMind 智能体联邦平台"
	@echo "=============================="
	@echo ""
	@echo "可用命令:"
	@echo "  help           - 显示此帮助信息"
	@echo "  install        - 安装Python依赖"
	@echo "  setup          - 初始化项目环境"
	@echo "  test           - 运行系统测试"
	@echo "  start          - 启动NexusMind服务器"
	@echo "  infrastructure - 启动基础设施服务 (Docker)"
	@echo "  stop           - 停止所有服务"
	@echo "  clean          - 清理临时文件"
	@echo "  status         - 检查服务状态"
	@echo "  format         - 格式化代码"
	@echo "  lint           - 代码质量检查"
	@echo ""

# 安装依赖
install:
	@echo "📦 安装Python依赖..."
	pip install -r requirements.txt
	@echo "✅ 依赖安装完成"

# 项目初始化设置
setup: install
	@echo "🔧 初始化项目环境..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ 已创建 .env 配置文件，请编辑其中的配置"; \
	else \
		echo "ℹ️  .env 文件已存在"; \
	fi
	@echo "🚀 项目初始化完成"
	@echo ""
	@echo "⚠️  重要提醒:"
	@echo "   1. 请编辑 .env 文件，设置 LLM_API_KEY"
	@echo "   2. 运行 'make infrastructure' 启动基础设施"
	@echo "   3. 运行 'make test' 测试系统功能"
	@echo "   4. 运行 'make start' 启动服务器"

# 启动基础设施服务
infrastructure:
	@echo "🐳 启动基础设施服务..."
	cd infrastructure && docker-compose up -d
	@echo "✅ 基础设施服务已启动"
	@echo "🔗 服务地址:"
	@echo "   - RabbitMQ Management: http://localhost:15672 (用户: nexusmind, 密码: nexusmind123)"
	@echo "   - Redis: localhost:6379"
	@echo "   - ChromaDB: http://localhost:8000"

# 运行测试
test:
	@echo "🧪 运行系统测试..."
	python test_system.py

# 启动服务器
start:
	@echo "🚀 启动NexusMind服务器..."
	python run_server.py

# 检查服务状态
status:
	@echo "📊 检查服务状态..."
	@echo ""
	@echo "🐳 Docker容器状态:"
	@docker ps --filter "name=nexusmind" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || echo "Docker未运行或无相关容器"
	@echo ""
	@echo "🌐 网络连接测试:"
	@curl -s http://localhost:8080/health > /dev/null && echo "✅ NexusMind API服务: 运行正常" || echo "❌ NexusMind API服务: 未运行"
	@curl -s http://localhost:15672 > /dev/null && echo "✅ RabbitMQ Management: 运行正常" || echo "❌ RabbitMQ Management: 未运行"
	@curl -s http://localhost:8000/api/v1/heartbeat > /dev/null && echo "✅ ChromaDB: 运行正常" || echo "❌ ChromaDB: 未运行"

# 停止所有服务
stop:
	@echo "⏹️  停止所有服务..."
	cd infrastructure && docker-compose down
	@echo "✅ 所有服务已停止"

# 清理临时文件
clean:
	@echo "🧹 清理临时文件..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ 清理完成"

# 代码格式化
format:
	@echo "🎨 格式化代码..."
	black backend/ --line-length 100
	@echo "✅ 代码格式化完成"

# 代码质量检查
lint:
	@echo "🔍 进行代码质量检查..."
	flake8 backend/ --max-line-length 100 --ignore E203,W503
	@echo "✅ 代码质量检查完成"

# 开发环境设置
dev: setup infrastructure
	@echo "🛠️  开发环境准备完成"
	@echo ""
	@echo "📝 开发工作流建议:"
	@echo "   1. make test    # 运行测试"
	@echo "   2. make start   # 启动服务器"
	@echo "   3. 打开 test_client.html 进行WebSocket测试"
	@echo "   4. 访问 http://localhost:8080/docs 查看API文档"

# 生产部署检查
check:
	@echo "🔍 生产部署检查..."
	@python -c "import backend.core.config; print('✅ 配置加载正常')"
	@python -c "from backend.core.orchestrator import NexusMindOrchestrator; NexusMindOrchestrator(); print('✅ 核心组件初始化正常')"
	@echo "✅ 部署检查完成"

# 日志查看
logs:
	@echo "📋 查看服务日志..."
	cd infrastructure && docker-compose logs -f

# 重启所有服务
restart: stop infrastructure
	@echo "🔄 重启完成"