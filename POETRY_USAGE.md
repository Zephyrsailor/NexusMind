# NexusMind Poetry 依赖管理指南

## 🎯 为什么选择Poetry？

NexusMind项目采用Poetry作为官方依赖管理工具，原因如下：

- ✅ **智能依赖解析**: 自动检测和解决依赖冲突
- ✅ **确定性构建**: poetry.lock确保团队环境一致性
- ✅ **开发依赖分离**: 自动管理开发和生产依赖
- ✅ **虚拟环境集成**: 自动创建和管理虚拟环境
- ✅ **现代标准**: 基于PEP 518/621标准

## 🚀 快速开始

### 1. 安装Poetry

```bash
# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# Windows PowerShell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -

# 添加到PATH
export PATH="$HOME/.local/bin:$PATH"
```

### 2. 项目设置

```bash
# 克隆项目
git clone <repository-url>
cd NexusMind

# 配置Poetry (推荐设置)
poetry config virtualenvs.in-project true  # 在项目目录创建.venv

# 安装依赖
poetry install

# 安装可选功能
poetry install --extras "all"  # 全部功能
poetry install --extras "speech"  # 语音功能
poetry install --extras "client"  # 客户端工具
poetry install --extras "ocr"     # OCR功能
```

### 3. 激活环境

```bash
# 激活虚拟环境
poetry shell

# 或直接运行命令
poetry run python run_server.py
```

## 📦 依赖管理

### 添加依赖

```bash
# 添加生产依赖
poetry add fastapi

# 添加开发依赖
poetry add --group dev pytest

# 添加可选依赖
poetry add --optional rich
```

### 更新依赖

```bash
# 更新所有依赖
poetry update

# 更新特定依赖
poetry update fastapi

# 查看过时依赖
poetry show --outdated
```

### 查看依赖

```bash
# 列出所有依赖
poetry show

# 查看依赖树
poetry show --tree

# 查看特定包信息
poetry show fastapi
```

## 🔧 常用命令

### 环境管理

```bash
# 查看虚拟环境信息
poetry env info

# 列出所有虚拟环境
poetry env list

# 删除虚拟环境
poetry env remove python
```

### 项目管理

```bash
# 检查项目配置
poetry check

# 构建项目
poetry build

# 发布到PyPI
poetry publish
```

## 🎯 NexusMind特定用法

### 完整安装 (推荐开发者)

```bash
# 核心功能安装 (推荐，避免编译问题)
poetry install --extras "core"
poetry run uvicorn backend.api.main:app --host 0.0.0.0 --port 8090 --reload

# 或完整功能 (需要编译pyaudio等)
poetry install --extras "all"
poetry run python run_server.py
```

### 最小安装 (仅API服务)

```bash
poetry install
poetry run uvicorn backend.api.main:app --host 0.0.0.0 --port 8090 --reload
```

### 客户端安装

```bash
poetry install --extras "client"
poetry run python nexusmind_simple_chat.py
```

### 语音功能

```bash
poetry install --extras "speech"
# 现在支持语音录制和识别
```

## ✅ 验证安装

```bash
# 启动服务 (推荐方式)
poetry run uvicorn backend.api.main:app --host 0.0.0.0 --port 8090 --reload

# 测试健康检查
curl http://localhost:8090/health

# 测试智能对话
curl -X POST "http://localhost:8090/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，Poetry环境测试"}'

# 查看API文档
open http://localhost:8090/docs
```

## 🔄 从requirements.txt迁移

如果你之前使用pip + requirements.txt：

```bash
# 1. 删除旧的虚拟环境
rm -rf venv

# 2. 使用Poetry安装
poetry install --extras "all"

# 3. 激活新环境
poetry shell
```

## 📝 最佳实践

### 1. 提交poetry.lock

```bash
# 总是提交poetry.lock文件
git add poetry.lock
git commit -m "Update dependencies"
```

### 2. 团队协作

```bash
# 新团队成员加入
poetry install  # 使用poetry.lock中的确切版本
```

### 3. CI/CD配置

```yaml
# GitHub Actions示例
- name: Install Poetry
  uses: snok/install-poetry@v1

- name: Install dependencies
  run: poetry install --extras "all"

- name: Run tests
  run: poetry run pytest
```

## 🆘 故障排除

### 常见问题

**Q: Poetry安装失败？**
```bash
# 使用pip安装
pip install poetry
```

**Q: 依赖冲突？**
```bash
# 清除缓存
poetry cache clear pypi --all
poetry install
```

**Q: 虚拟环境问题？**
```bash
# 重新创建虚拟环境
poetry env remove python
poetry install
```

## 🔗 相关链接

- [Poetry官方文档](https://python-poetry.org/docs/)
- [依赖管理最佳实践](https://packaging.python.org/)
- [PEP 518规范](https://www.python.org/dev/peps/pep-0518/) 