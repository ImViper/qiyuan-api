# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述 / Project Overview

这是一个基于 Go 的 AI 模型网关系统，从 New API 项目分叉而来（New API 本身基于 One API）。该系统为多种 AI 模型提供统一的 API 网关服务，包含 Go 后端和 React 前端。

This is a Go-based AI model gateway system forked from New API (which is based on One API). It provides unified API gateway services for multiple AI models with a Go backend and React frontend.

## 开发环境设置 / Development Environment Setup

### 后端开发 / Backend Development

```bash
# 开发环境启动后端 / Start backend in development
go run main.go

# 构建后端 / Build backend
go build -o new-api main.go

# 使用环境变量 / With environment variables
SQL_DSN="sqlite:data/new-api.db" go run main.go
```

### 前端开发 / Frontend Development

```bash
# 进入前端目录 / Navigate to frontend directory
cd web

# 安装依赖 / Install dependencies  
bun install

# 开发模式启动 / Start development server
bun run dev

# 构建前端 / Build frontend
DISABLE_ESLINT_PLUGIN='true' VITE_REACT_APP_VERSION=$(cat ../VERSION) bun run build

# 代码格式化 / Code formatting
bun run lint:fix
```

### 完整构建 / Full Build

```bash
# 使用 Makefile 构建完整应用 / Build full application with Makefile
make all

# 或分步执行 / Or step by step
make build-frontend
make start-backend
```

### Docker 开发 / Docker Development

```bash
# 使用 Docker Compose 启动完整环境 / Start full environment with Docker Compose
docker-compose up -d

# 查看日志 / View logs
docker-compose logs -f new-api

# 重建镜像 / Rebuild images
docker-compose up -d --build
```

## 代码架构 / Code Architecture

### 后端架构 (Go) / Backend Architecture (Go)

系统采用经典的 MVC 架构模式：

**核心目录结构：**
- `main.go` - 应用程序入口点，服务器初始化
- `common/` - 公共工具、配置、常量
- `controller/` - HTTP 处理器和业务逻辑
- `model/` - 数据模型和数据库操作  
- `middleware/` - HTTP 中间件（认证、限流、日志等）
- `router/` - 路由配置和端点定义
- `relay/` - AI 模型适配器和代理逻辑
- `service/` - 业务服务层
- `dto/` - 数据传输对象
- `constant/` - 常量定义

**关键组件：**

1. **Channel System (`relay/channel/`)**: 为不同 AI 提供商（OpenAI、Claude、Gemini 等）提供适配器模式实现
2. **Authentication & Authorization (`middleware/auth.go`)**: JWT 令牌验证和用户权限管理
3. **Rate Limiting (`middleware/rate-limit.go`)**: 多层限流机制
4. **Relay System (`relay/`)**: 核心代理逻辑，处理请求转发和响应
5. **Caching Layer (`model/*_cache.go`)**: Redis/内存缓存实现
6. **Database Layer (`model/`)**: GORM ORM，支持 SQLite、MySQL、PostgreSQL

### 前端架构 (React) / Frontend Architecture (React)

现代 React 应用，使用 Vite 构建：

**技术栈：**
- React 18 + React Router
- Semi Design UI 库
- Axios HTTP 客户端  
- i18next 国际化
- VChart 数据可视化

**目录结构：**
- `src/components/` - 可复用组件
- `src/pages/` - 页面组件
- `src/hooks/` - 自定义 React hooks
- `src/context/` - React Context 状态管理
- `src/helpers/` - 工具函数

## 数据库 / Database

系统支持多种数据库：
- **开发环境**: SQLite (默认)
- **生产环境**: MySQL 5.7.8+, PostgreSQL 9.6+

**环境变量配置：**
```bash
# SQLite
SQL_DSN="sqlite:data/new-api.db"

# MySQL  
SQL_DSN="user:password@tcp(localhost:3306)/database"

# PostgreSQL
SQL_DSN="host=localhost user=username password=password dbname=database sslmode=disable"
```

## 环境变量配置 / Environment Variables

### 核心配置 / Core Configuration

```bash
# 数据库连接 / Database
SQL_DSN="sqlite:data/new-api.db"

# Redis 缓存 / Redis Cache  
REDIS_CONN_STRING="redis://localhost:6379"
MEMORY_CACHE_ENABLED=true

# 服务器配置 / Server Configuration
PORT=3000
GIN_MODE=debug  # 或 release

# 会话安全 / Session Security (多机部署必需)
SESSION_SECRET="your-secret-key"
CRYPTO_SECRET="your-crypto-key"

# 节点配置 / Node Configuration
NODE_TYPE=master  # 或 slave
SYNC_FREQUENCY=60
```

### 功能配置 / Feature Configuration

```bash
# 日志和调试 / Logging & Debug
ERROR_LOG_ENABLED=true
ENABLE_PPROF=true

# 安全设置 / Security
STREAMING_TIMEOUT=120
FORCE_STREAM_OPTION=true

# AI 模型配置 / AI Model Configuration
GEMINI_VISION_MAX_IMAGE_NUM=16
COHERE_SAFETY_SETTING=NONE
AZURE_DEFAULT_API_VERSION="2025-04-01-preview"
```

## 测试 / Testing

**渠道测试：**
系统包含内置的渠道测试功能 (`controller/channel-test.go`)，用于验证 AI 提供商连接。

**手动测试渠道：**
```bash
# 通过管理界面或 API 端点测试特定渠道
# 位于 /api/channel/test/{channel_id}
```

**性能测试：**
```bash
# 启用 pprof 性能分析
ENABLE_PPROF=true go run main.go
# 访问 http://localhost:8005/debug/pprof/
```

## 部署注意事项 / Deployment Notes

### 多机部署 / Multi-Node Deployment

多机部署时必须设置：
```bash
SESSION_SECRET="same-value-across-all-nodes"
CRYPTO_SECRET="same-value-across-all-nodes"  # 如果使用共享 Redis
```

### Docker 部署 / Docker Deployment

确保挂载数据目录：
```bash
docker run -v /host/data:/data calciumion/new-api:latest
```

### 生产环境优化 / Production Optimization

```bash
GIN_MODE=release
BATCH_UPDATE_ENABLED=true
MEMORY_CACHE_ENABLED=true
```

## 关键 API 端点 / Key API Endpoints

- `/api/relay/` - AI 模型代理端点
- `/api/channel/` - 渠道管理
- `/api/user/` - 用户管理  
- `/api/token/` - 令牌管理
- `/api/log/` - 日志查询
- `/api/status` - 系统状态

## 开发工作流 / Development Workflow

1. **前端开发**: 在 `web/` 目录使用 `bun run dev`
2. **后端开发**: 根目录使用 `go run main.go`  
3. **完整测试**: 使用 `make all` 构建并测试
4. **生产构建**: 使用 Docker 或二进制构建