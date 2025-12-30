#!/bin/bash

# qiyuan-api Docker 更新脚本
# 使用方法: ./update.sh [选项]
# 选项:
#   --skip-backup    跳过数据库备份
#   --no-rebuild     不重新构建镜像，只重启
#   --pull-only      只拉取代码，不部署

set -e  # 出错时退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PROJECT_DIR="/opt/qiyuan-api"  # 修改为你的项目路径
BACKUP_DIR="/backup/qiyuan-api"
DB_PASSWORD="123456"  # 修改为你的数据库密码
DB_NAME="new-api"

# 参数解析
SKIP_BACKUP=false
NO_REBUILD=false
PULL_ONLY=false

for arg in "$@"; do
    case $arg in
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --no-rebuild)
            NO_REBUILD=true
            shift
            ;;
        --pull-only)
            PULL_ONLY=true
            shift
            ;;
    esac
done

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否在项目目录
check_directory() {
    if [ ! -f "docker-compose.yml" ]; then
        log_error "未找到 docker-compose.yml，请在项目根目录执行此脚本"
        log_info "当前目录: $(pwd)"
        log_info "请使用: cd $PROJECT_DIR && ./update.sh"
        exit 1
    fi
}

# 创建备份目录
create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_info "创建备份目录: $BACKUP_DIR"
    fi
}

# 备份数据库
backup_database() {
    if [ "$SKIP_BACKUP" = true ]; then
        log_warning "跳过数据库备份"
        return
    fi

    log_info "开始备份数据库..."
    local backup_file="$BACKUP_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql"

    if docker exec mysql mysqldump -u root -p"$DB_PASSWORD" "$DB_NAME" > "$backup_file" 2>/dev/null; then
        log_success "数据库备份成功: $backup_file"

        # 压缩备份
        gzip "$backup_file"
        log_success "备份已压缩: ${backup_file}.gz"

        # 清理7天前的备份
        find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +7 -delete
        log_info "已清理7天前的旧备份"
    else
        log_warning "数据库备份失败，继续执行..."
    fi
}

# 备份数据文件
backup_data() {
    if [ "$SKIP_BACKUP" = true ]; then
        return
    fi

    log_info "备份数据文件..."
    if [ -d "./data" ]; then
        local data_backup="$BACKUP_DIR/data_backup_$(date +%Y%m%d)"
        cp -r ./data "$data_backup" 2>/dev/null || log_warning "数据文件备份失败"
        log_success "数据文件已备份"
    fi
}

# 拉取最新代码
pull_code() {
    log_info "拉取最新代码..."

    # 检查当前分支
    local current_branch=$(git branch --show-current)
    log_info "当前分支: $current_branch"

    # 检查是否有未提交的更改
    if ! git diff-index --quiet HEAD --; then
        log_warning "检测到未提交的更改，请先处理"
        git status --short
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    # 获取更新前的提交
    local old_commit=$(git rev-parse --short HEAD)

    # 拉取代码
    git fetch origin
    git pull origin "$current_branch"

    # 获取更新后的提交
    local new_commit=$(git rev-parse --short HEAD)

    if [ "$old_commit" = "$new_commit" ]; then
        log_info "代码已是最新，无需更新"
        return 1
    else
        log_success "代码更新成功: $old_commit -> $new_commit"

        # 显示变更
        log_info "最近的变更:"
        git log --oneline "$old_commit..$new_commit" | head -10
        return 0
    fi
}

# 检查配置更新
check_config_updates() {
    log_info "检查配置文件更新..."

    if git diff HEAD~1 docker-compose.yml | grep -q "environment:" || git diff HEAD~1 docker-compose.yml | grep -q "^+.*-.*:"; then
        log_warning "检测到 docker-compose.yml 配置部分有更新"
        log_warning "请检查是否有新的环境变量需要配置"
        log_info "查看差异: git diff HEAD~1 docker-compose.yml"
        read -p "是否查看差异? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git diff HEAD~1 docker-compose.yml | grep -A 20 "environment:"
        fi
    fi
}

# 检查依赖更新
check_dependencies() {
    log_info "检查依赖更新..."

    if git diff HEAD~1 go.mod go.sum | grep -q "^+"; then
        log_warning "检测到 Go 依赖有更新，需要重新构建"
        NO_REBUILD=false
    fi

    if git diff HEAD~1 web/package.json web/bun.lock | grep -q "^+"; then
        log_warning "检测到前端依赖有更新，需要重新构建"
        NO_REBUILD=false
    fi
}

# 停止服务
stop_services() {
    log_info "停止服务..."
    docker-compose down
    log_success "服务已停止"
}

# 构建镜像
build_image() {
    if [ "$NO_REBUILD" = true ]; then
        log_info "跳过镜像重新构建"
        return
    fi

    log_info "开始构建镜像（这可能需要几分钟）..."
    docker-compose build --no-cache
    log_success "镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    docker-compose up -d
    log_success "服务已启动"

    # 等待服务启动
    log_info "等待服务就绪..."
    sleep 5
}

# 检查服务状态
check_health() {
    log_info "检查服务状态..."

    # 检查容器状态
    if docker-compose ps | grep -q "Up"; then
        log_success "容器运行正常"
    else
        log_error "容器启动失败"
        docker-compose ps
        exit 1
    fi

    # 检查健康状态
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -sf http://localhost:3000/api/status > /dev/null 2>&1; then
            log_success "健康检查通过"
            return 0
        fi

        log_info "等待服务就绪... ($attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done

    log_error "健康检查失败"
    log_info "查看日志:"
    docker-compose logs --tail=50 new-api
    exit 1
}

# 显示状态
show_status() {
    log_info "当前状态:"
    docker-compose ps

    log_info "\n最近日志:"
    docker-compose logs --tail=20 new-api

    log_info "\n资源使用:"
    docker stats --no-stream new-api mysql redis
}

# 清理旧镜像
cleanup() {
    log_info "清理未使用的镜像..."
    docker image prune -f > /dev/null 2>&1 || true
    log_success "清理完成"
}

# 主流程
main() {
    echo "======================================"
    echo "   qiyuan-api Docker 更新脚本"
    echo "======================================"
    echo ""

    # 检查目录
    check_directory

    # 创建备份目录
    create_backup_dir

    # 备份
    backup_database
    backup_data

    # 拉取代码
    if ! pull_code; then
        if [ "$PULL_ONLY" = true ]; then
            log_info "代码已是最新，退出"
            exit 0
        fi
    fi

    if [ "$PULL_ONLY" = true ]; then
        log_success "代码拉取完成"
        exit 0
    fi

    # 检查更新
    check_config_updates
    check_dependencies

    # 确认更新
    echo ""
    log_warning "即将更新服务，这将导致短暂的服务中断"
    read -p "是否继续? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "更新已取消"
        exit 0
    fi

    # 部署
    stop_services
    build_image
    start_services
    check_health

    # 显示状态
    echo ""
    show_status

    # 清理
    cleanup

    echo ""
    echo "======================================"
    log_success "更新完成！"
    echo "======================================"
    echo ""
    log_info "访问地址: http://$(hostname -I | awk '{print $1}'):51099"
    log_info "查看日志: docker-compose logs -f new-api"
    log_info "查看状态: docker-compose ps"
}

# 执行主流程
main
