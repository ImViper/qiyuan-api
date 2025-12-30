# Docker 部署快速参考

## 📌 常用命令速查

### 快速更新（推荐）
```bash
# 使用自动更新脚本
chmod +x update.sh
./update.sh

# 跳过备份（开发环境）
./update.sh --skip-backup

# 只拉取代码不部署
./update.sh --pull-only

# 不重新构建镜像（仅配置变更）
./update.sh --no-rebuild
```

### 手动操作

#### 启动服务
```bash
docker-compose up -d
```

#### 停止服务
```bash
docker-compose down
```

#### 重启服务
```bash
docker-compose restart
```

#### 重新构建并启动
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

#### 查看日志
```bash
# 实时日志
docker-compose logs -f

# 只看 new-api
docker-compose logs -f new-api

# 最近 100 行
docker-compose logs --tail=100 new-api
```

#### 查看状态
```bash
# 容器状态
docker-compose ps

# 资源使用
docker stats

# 健康检查
curl http://localhost:51099/api/status
```

### 数据库操作

#### 备份数据库
```bash
docker exec mysql mysqldump -u root -p123456 new-api > backup.sql
```

#### 恢复数据库
```bash
docker exec -i mysql mysql -u root -p123456 new-api < backup.sql
```

#### 连接数据库
```bash
docker exec -it mysql mysql -u root -p123456 new-api
```

### 故障排查

#### 查看容器日志
```bash
docker logs new-api
docker logs mysql
docker logs redis
```

#### 进入容器
```bash
docker exec -it new-api sh
docker exec -it mysql bash
docker exec -it redis sh
```

#### 重启单个服务
```bash
docker-compose restart new-api
docker-compose restart mysql
```

#### 清理资源
```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的容器
docker container prune

# 清理所有
docker system prune -a
```

## 🔄 完整更新流程

### 1. 准备
```bash
cd /opt/qiyuan-api
git fetch origin
git log --oneline HEAD..origin/qiyuan-api  # 查看更新
```

### 2. 备份
```bash
# 备份数据库
docker exec mysql mysqldump -u root -pYOUR_PASSWORD new-api > backup_$(date +%Y%m%d).sql

# 备份数据文件
cp -r ./data ./data.backup.$(date +%Y%m%d)
```

### 3. 更新代码
```bash
git pull origin qiyuan-api
```

### 4. 检查配置
```bash
# 查看配置差异
diff .env.example .env

# 更新配置
nano .env
```

### 5. 部署
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 6. 验证
```bash
# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f new-api

# 测试 API
curl http://localhost:51099/api/status
```

## 🚨 应急处理

### 服务无法启动
```bash
# 1. 查看日志
docker-compose logs new-api

# 2. 检查配置
docker-compose config

# 3. 重启所有服务
docker-compose down
docker-compose up -d
```

### 数据库连接失败
```bash
# 1. 检查 MySQL 状态
docker-compose ps mysql

# 2. 测试连接
docker exec mysql mysql -u root -pYOUR_PASSWORD -e "SELECT 1;"

# 3. 检查配置一致性
grep SQL_DSN .env
grep MYSQL_ROOT_PASSWORD docker-compose.yml
```

### 端口冲突
```bash
# 1. 查看端口占用
netstat -tlnp | grep 51099

# 2. 修改端口映射
nano docker-compose.yml
# 修改 ports: "51099:3000" 为其他端口

# 3. 重启
docker-compose up -d
```

### 回滚到之前版本
```bash
# 1. 查看提交历史
git log --oneline -10

# 2. 回滚代码
git reset --hard COMMIT_HASH

# 3. 重新部署
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 4. 恢复数据库（如有必要）
docker exec -i mysql mysql -u root -pYOUR_PASSWORD new-api < backup.sql
```

## 📊 监控和维护

### 查看资源使用
```bash
# 实时监控
docker stats

# 磁盘使用
du -sh ./data ./logs
df -h
```

### 清理日志
```bash
# 清理 Docker 日志
truncate -s 0 $(docker inspect --format='{{.LogPath}}' new-api)

# 清理应用日志
rm -rf ./logs/*.log
```

### 定期维护
```bash
# 每周运行一次
docker system prune -f
docker volume prune -f

# 优化数据库
docker exec mysql mysqlcheck -u root -pYOUR_PASSWORD --optimize --all-databases
```

## 🔐 安全检查清单

- [ ] 修改了 MySQL root 密码
- [ ] 修改了 SESSION_SECRET
- [ ] 修改了管理员密码
- [ ] 配置了防火墙规则
- [ ] 启用了 HTTPS（生产环境）
- [ ] 设置了自动备份
- [ ] 限制了数据库外部访问
- [ ] 定期更新系统和 Docker

## 📝 配置项说明

### 必须配置
```bash
SQL_DSN=root:YOUR_PASSWORD@tcp(mysql:3306)/new-api
SESSION_SECRET=your_random_secret_here
TZ=Asia/Shanghai
```

### 性能优化
```bash
BATCH_UPDATE_ENABLED=true
BATCH_UPDATE_INTERVAL=5
CHANNEL_UPDATE_FREQUENCY=30
```

### 新功能配置（v0.10+）
```bash
# Pyroscope 性能监控
PYROSCOPE_URL=http://localhost:4040
PYROSCOPE_APP_NAME=qiyuan-api

# Discord OAuth
DISCORD_CLIENT_ID=your_client_id
DISCORD_CLIENT_SECRET=your_client_secret

# IO.NET 集成
IONET_API_KEY=your_api_key

# 任务查询限制
TASK_QUERY_LIMIT=100
```

## 🌐 反向代理配置

### Nginx 示例
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:51099;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Caddy 示例
```
your-domain.com {
    reverse_proxy localhost:51099
}
```

## 📞 获取帮助

- 详细部署指南: `DEPLOY_GUIDE.md`
- 更新日志: `UPSTREAM_CHANGELOG.md`
- 问题反馈: https://github.com/ImViper/qiyuan-api/issues

---

**更新日期**: 2025-12-31
