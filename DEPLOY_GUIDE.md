# 远端 Docker 部署指南

本指南适用于将 qiyuan-api 部署到远端服务器。

---

## 📋 部署前准备

### 1. 服务器要求
- Docker 20.10+
- Docker Compose 1.29+
- 至少 2GB RAM
- 至少 10GB 可用磁盘空间
- Git 已安装

### 2. 检查 Docker 环境
```bash
docker --version
docker-compose --version
```

---

## 🚀 首次部署流程

### 步骤 1: 克隆或更新代码

#### 首次克隆
```bash
cd /opt  # 或你的部署目录
git clone https://github.com/ImViper/qiyuan-api.git
cd qiyuan-api
```

#### 已有代码，需要更新
```bash
cd /opt/qiyuan-api  # 你的项目路径

# 备份当前配置
cp .env .env.backup.$(date +%Y%m%d)

# 拉取最新代码
git fetch origin
git pull origin qiyuan-api

# 查看变更
git log --oneline -10
```

---

### 步骤 2: 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
nano .env  # 或使用 vim
```

**必须修改的配置项：**
```bash
# 数据库密码（必须修改！）
# 同时修改 docker-compose.yml 中的 MYSQL_ROOT_PASSWORD
SQL_DSN=root:YOUR_STRONG_PASSWORD@tcp(mysql:3306)/new-api

# Session 密钥（多机部署必须设置）
SESSION_SECRET=your_random_string_here_change_this

# 时区
TZ=Asia/Shanghai

# Redis
REDIS_CONN_STRING=redis://redis

# 日志
ERROR_LOG_ENABLED=true
BATCH_UPDATE_ENABLED=true
```

**可选配置（根据需要）：**
```bash
# Pyroscope 性能监控（新增功能）
# PYROSCOPE_URL=http://localhost:4040
# PYROSCOPE_APP_NAME=qiyuan-api

# Discord OAuth（新增功能）
# DISCORD_CLIENT_ID=your_client_id
# DISCORD_CLIENT_SECRET=your_client_secret

# IO.NET 集成（新增功能）
# IONET_API_KEY=your_api_key

# 任务查询限制
# TASK_QUERY_LIMIT=100

# 流式超时
# STREAMING_TIMEOUT=300
```

---

### 步骤 3: 修改 docker-compose.yml

**重要：修改数据库密码**
```bash
nano docker-compose.yml
```

找到以下行并修改密码：
```yaml
  mysql:
    environment:
      MYSQL_ROOT_PASSWORD: YOUR_STRONG_PASSWORD  # ⚠️ 修改这里
      MYSQL_DATABASE: new-api
```

同时修改 new-api 服务的 SQL_DSN：
```yaml
  new-api:
    environment:
      - SQL_DSN=root:YOUR_STRONG_PASSWORD@tcp(mysql:3306)/new-api
```

**可选：修改端口映射**
```yaml
  new-api:
    ports:
      - "51099:3000"  # 改为你需要的端口，如 "8080:3000"
```

---

### 步骤 4: 构建和启动

#### 方案 A: 使用 Docker Compose 构建（推荐）
```bash
# 停止旧容器（如果存在）
docker-compose down

# 构建新镜像
docker-compose build --no-cache

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f new-api
```

#### 方案 B: 使用预构建镜像（更快）
```bash
# 修改 docker-compose.yml，将第19行取消注释，第20行注释掉
# build: .  # 注释这行
# image: calciumion/new-api:latest  # 取消注释这行

# 拉取最新镜像
docker-compose pull

# 启动服务
docker-compose up -d
```

---

## 🔄 更新部署流程（已有运行中的服务）

### 快速更新脚本
```bash
#!/bin/bash
# save as: update.sh

set -e  # 出错时退出

echo "开始更新 qiyuan-api..."

# 1. 拉取最新代码
echo "拉取最新代码..."
git fetch origin
git pull origin qiyuan-api

# 2. 备份数据库（可选但推荐）
echo "备份数据库..."
docker exec mysql mysqldump -u root -p123456 new-api > backup_$(date +%Y%m%d_%H%M%S).sql

# 3. 停止并删除旧容器
echo "停止旧服务..."
docker-compose down

# 4. 重新构建镜像
echo "构建新镜像..."
docker-compose build --no-cache

# 5. 启动新容器
echo "启动新服务..."
docker-compose up -d

# 6. 查看状态
echo "检查服务状态..."
sleep 5
docker-compose ps

# 7. 查看日志
echo "最近日志："
docker-compose logs --tail=50 new-api

echo "更新完成！"
```

使用方法：
```bash
chmod +x update.sh
./update.sh
```

---

### 手动更新步骤

#### 1. 备份数据（重要！）
```bash
# 备份数据库
docker exec mysql mysqldump -u root -pYOUR_PASSWORD new-api > backup_$(date +%Y%m%d).sql

# 备份数据文件
cp -r ./data ./data.backup.$(date +%Y%m%d)
```

#### 2. 拉取最新代码
```bash
cd /opt/qiyuan-api
git pull origin qiyuan-api
```

#### 3. 查看变更
```bash
# 查看最新提交
git log --oneline -10

# 查看 UPSTREAM_CHANGELOG.md 了解新功能
cat UPSTREAM_CHANGELOG.md | head -100
```

#### 4. 更新依赖（如果 go.mod 有变化）
```bash
# 检查是否需要更新依赖
git diff HEAD~1 go.mod go.sum

# 如果有变化，需要重新构建
```

#### 5. 更新环境变量
```bash
# 对比新旧配置
diff .env.example .env

# 添加新的配置项（如 Pyroscope、Discord 等）
nano .env
```

#### 6. 停止并重建
```bash
# 停止服务
docker-compose down

# 清理旧镜像（可选，释放空间）
docker image prune -f

# 重新构建
docker-compose build --no-cache

# 启动服务
docker-compose up -d
```

#### 7. 检查健康状态
```bash
# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f new-api

# 检查健康检查
docker inspect new-api | grep -A 10 Health
```

---

## 📊 数据库迁移

### 检查是否需要迁移
```bash
# 查看 model/ 目录的变更
git diff HEAD~255 model/

# 如果有 schema 变更，可能需要手动迁移
```

### 执行迁移（如果需要）
```bash
# 连接到数据库
docker exec -it mysql mysql -u root -pYOUR_PASSWORD new-api

# 查看表结构
SHOW TABLES;
DESCRIBE users;  # 示例

# 退出
exit;
```

程序会在启动时自动执行 GORM 迁移，通常不需要手动干预。

---

## 🔍 验证部署

### 1. 检查服务状态
```bash
# 检查所有容器
docker-compose ps

# 应该看到：
# new-api    Up (healthy)
# mysql      Up
# redis      Up
```

### 2. 测试 API
```bash
# 健康检查
curl http://localhost:51099/api/status

# 应该返回：
# {"success":true,"message":""}
```

### 3. 访问 Web 界面
```
http://YOUR_SERVER_IP:51099
```

### 4. 查看日志
```bash
# 实时日志
docker-compose logs -f

# 只看 new-api 服务
docker-compose logs -f new-api

# 最近 100 行
docker-compose logs --tail=100 new-api
```

---

## 🛠️ 常见问题处理

### 问题 1: 容器启动失败
```bash
# 查看详细日志
docker-compose logs new-api

# 检查配置
docker-compose config

# 重启所有服务
docker-compose restart
```

### 问题 2: 数据库连接失败
```bash
# 检查 MySQL 是否运行
docker-compose ps mysql

# 测试数据库连接
docker exec -it mysql mysql -u root -pYOUR_PASSWORD -e "SELECT 1;"

# 检查密码是否一致
grep SQL_DSN .env
grep MYSQL_ROOT_PASSWORD docker-compose.yml
```

### 问题 3: 端口冲突
```bash
# 检查端口占用
netstat -tlnp | grep 51099

# 修改 docker-compose.yml 中的端口映射
# "51099:3000" 改为 "8080:3000"
```

### 问题 4: 磁盘空间不足
```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的容器
docker container prune

# 清理未使用的卷
docker volume prune

# 查看磁盘使用
docker system df
```

### 问题 5: 构建缓慢
```bash
# 使用预构建镜像代替本地构建
# 修改 docker-compose.yml:
# image: calciumion/new-api:latest

# 然后：
docker-compose pull
docker-compose up -d
```

---

## 🔐 安全建议

### 1. 修改默认密码
- MySQL root 密码
- SESSION_SECRET
- 管理员账号密码（Web 界面）

### 2. 配置防火墙
```bash
# 只开放必要端口
ufw allow 51099/tcp  # new-api
ufw enable
```

### 3. 使用 HTTPS
推荐使用 Nginx 或 Caddy 作为反向代理：
```bash
# 安装 Nginx
apt install nginx

# 配置 SSL
# 使用 Let's Encrypt 免费证书
```

### 4. 定期备份
```bash
# 添加 cron 任务
crontab -e

# 每天凌晨 2 点备份
0 2 * * * cd /opt/qiyuan-api && docker exec mysql mysqldump -u root -pYOUR_PASSWORD new-api > /backup/new-api_$(date +\%Y\%m\%d).sql
```

---

## 📈 监控和维护

### 查看资源使用
```bash
# 容器资源使用
docker stats

# 磁盘使用
du -sh ./data ./logs
```

### 日志轮转
```bash
# 限制日志大小（修改 docker-compose.yml）
services:
  new-api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 定期更新
建议每 1-2 周检查上游更新：
```bash
git fetch --all
git log qiyuan-api..origin/qiyuan-api --oneline
```

---

## 📞 获取帮助

- 查看更新日志: `cat UPSTREAM_CHANGELOG.md`
- 上游文档: https://github.com/QuantumNous/new-api
- Issue 反馈: https://github.com/ImViper/qiyuan-api/issues

---

**最后更新**: 2025-12-31
**适用版本**: v0.10.5+
