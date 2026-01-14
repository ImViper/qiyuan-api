# Docker 部署简明指南

> 适用于使用 Docker Compose 的部署方式

---

## ⚡ 快速开始

### 远端服务器更新部署（3步完成）

```bash
# 1. 拉取最新代码
cd /opt/qiyuan-api  # 你的项目路径
git pull origin qiyuan-api

# 2. 重新构建和启动
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 3. 查看状态
docker-compose logs -f new-api
```

就这么简单！

---

## 📝 配置说明

### Docker 部署的配置方式

**重要**：Docker 部署时，所有配置都在 `docker-compose.yml` 文件中，**不需要** `.env` 文件。

`.env` 文件只用于非 Docker 部署（直接运行编译后的二进制文件）。

### 需要修改的配置

打开 `docker-compose.yml`，修改以下部分：

#### 1. 数据库密码（必须修改）

```yaml
# 第 31 行 - new-api 服务的数据库连接
environment:
  - SQL_DSN=root:YOUR_PASSWORD@tcp(mysql:3306)/new-api  # 改这里

# 第 73 行 - mysql 服务的密码
mysql:
  environment:
    MYSQL_ROOT_PASSWORD: YOUR_PASSWORD  # 改这里，要和上面一致
```

#### 2. 端口映射（可选）

```yaml
# 第 25 行
ports:
  - "51099:3000"  # 改为你需要的端口，如 "8080:3000"
```

#### 3. Session 密钥（多机部署必须设置）

```yaml
# 第 37 行，取消注释并修改
environment:
  - SESSION_SECRET=your_random_string_here  # 去掉前面的 #
```

#### 4. 新功能配置（v0.10+ 可选）

在 `environment:` 部分添加：

```yaml
# Pyroscope 性能监控
# - PYROSCOPE_URL=http://your-pyroscope:4040
# - PYROSCOPE_APP_NAME=qiyuan-api

# Discord OAuth
# - DISCORD_CLIENT_ID=your_client_id
# - DISCORD_CLIENT_SECRET=your_client_secret

# IO.NET 集成
# - IONET_API_KEY=your_api_key

# 任务查询限制
# - TASK_QUERY_LIMIT=100

# 流式超时
# - STREAMING_TIMEOUT=300
```

---

## 🚀 完整部署流程

### 首次部署

```bash
# 1. 克隆项目
cd /opt
git clone https://github.com/ImViper/qiyuan-api.git
cd qiyuan-api

# 2. 修改配置
nano docker-compose.yml
# 修改数据库密码（两处）
# 修改端口（如需要）
# 添加 SESSION_SECRET（如果多机部署）

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f new-api
```

### 更新部署

```bash
# 1. 进入项目目录
cd /opt/qiyuan-api

# 2. 备份数据库（推荐）
docker exec mysql mysqldump -u root -pYOUR_PASSWORD new-api > backup_$(date +%Y%m%d).sql

# 3. 拉取最新代码
git pull origin qiyuan-api

# 4. 检查配置是否有新增项
git diff HEAD~1 docker-compose.yml

# 5. 重新构建部署
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 6. 验证
docker-compose ps
curl http://localhost:51099/api/status
```

---

## 🔧 常用命令

### 服务管理

```bash
# 启动
docker-compose up -d

# 停止
docker-compose down

# 重启
docker-compose restart

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f new-api
```

### 数据库操作

```bash
# 备份
docker exec mysql mysqldump -u root -pYOUR_PASSWORD new-api > backup.sql

# 恢复
docker exec -i mysql mysql -u root -pYOUR_PASSWORD new-api < backup.sql

# 连接数据库
docker exec -it mysql mysql -u root -pYOUR_PASSWORD new-api
```

---

## 📊 最新更新重点（v0.10.5+ → v0.10.6-alpha.2）

### 主要新增功能

1. **签到功能** - 用户签到系统 + Turnstile 安全验证
2. **Claude Opus 4.5** - 最新最强的 Claude 模型
3. **Doubao Video 1.5** - 字节跳动视频生成
4. **状态码自动禁用** - 自动管理异常渠道
5. **Gemini 修复** - 多个关键问题修复
6. **计费修复** - Anthropic、智谱、Moonshot 计费问题

### 需要注意

- **320 个新提交**，建议先备份数据库
- **依赖有更新**，需要重新构建镜像（`--no-cache`）
- **数据库会自动迁移**（新增 checkin 表），无需手动操作
- **新增配置项**都是可选的，不影响现有功能
- **签到功能**需要配置 Turnstile 才能启用

详见：`UPSTREAM_CHANGELOG.md`

---

## 🔍 验证部署

```bash
# 1. 容器状态
docker-compose ps
# 应该看到 new-api, mysql, redis 都是 Up

# 2. 健康检查
curl http://localhost:51099/api/status
# 返回: {"success":true,"message":""}

# 3. 访问界面
# http://YOUR_SERVER_IP:51099

# 4. 查看资源
docker stats
```

---

## 🚨 故障排查

### 服务无法启动

```bash
# 查看日志找原因
docker-compose logs new-api

# 检查配置语法
docker-compose config

# 完全重启
docker-compose down
docker system prune -f
docker-compose up -d
```

### 数据库连接失败

```bash
# 检查密码是否一致
grep "SQL_DSN" docker-compose.yml
grep "MYSQL_ROOT_PASSWORD" docker-compose.yml

# 测试数据库
docker exec mysql mysql -u root -pYOUR_PASSWORD -e "SELECT 1;"
```

### 端口冲突

```bash
# 查看端口占用
netstat -tlnp | grep 51099

# 修改端口
nano docker-compose.yml
# 改 ports: "51099:3000" 为其他端口
```

---

## 🔐 安全检查清单

- [ ] 已修改数据库密码（docker-compose.yml 两处）
- [ ] 已设置 SESSION_SECRET（多机部署）
- [ ] 已修改 Web 管理员密码
- [ ] 已配置防火墙
- [ ] 已限制数据库外部访问（如不需要）
- [ ] 已设置定期备份

---

## 💡 实用技巧

### 使用预构建镜像（更快）

不想每次都构建？使用官方镜像：

```yaml
# 修改 docker-compose.yml 第 19-20 行
services:
  new-api:
    # build: .  # 注释这行
    image: calciumion/new-api:latest  # 取消注释这行
```

然后：
```bash
docker-compose pull
docker-compose up -d
```

### 限制日志大小

在 `docker-compose.yml` 中添加：

```yaml
services:
  new-api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 反向代理（Nginx）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:51099;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 📞 获取帮助

- 更新日志：`cat UPSTREAM_CHANGELOG.md | head -300`
- 问题反馈：https://github.com/ImViper/qiyuan-api/issues
- 上游文档：https://github.com/QuantumNous/new-api

---

**更新日期**: 2025-12-31
**适用版本**: v0.10.5+
**部署方式**: Docker Compose
