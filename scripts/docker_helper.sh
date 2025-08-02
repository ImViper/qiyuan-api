#!/bin/bash

# Docker Compose 渠道管理助手脚本
# 用于简化在 Docker Compose 环境下的渠道管理操作

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 默认配置
MYSQL_DSN="root:123456@tcp(localhost:3306)/new-api"
MYSQL_CONTAINER="mysql"
COMPOSE_FILE="../docker-compose.yml"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 检查 Docker Compose 服务状态
check_services() {
    log_info "检查 Docker Compose 服务状态..."
    
    if ! docker-compose -f "$COMPOSE_FILE" ps | grep -q "mysql.*Up"; then
        log_error "MySQL 服务未运行"
        echo "请先启动 Docker Compose 服务:"
        echo "  cd .. && docker-compose up -d"
        return 1
    fi
    
    log_success "MySQL 服务正在运行"
    return 0
}

# 等待 MySQL 服务就绪
wait_for_mysql() {
    log_info "等待 MySQL 服务就绪..."
    
    local retry_count=0
    local max_retries=30
    
    while [ $retry_count -lt $max_retries ]; do
        if docker exec "$MYSQL_CONTAINER" mysqladmin ping -uroot -p123456 --silent 2>/dev/null; then
            log_success "MySQL 服务已就绪"
            return 0
        fi
        
        retry_count=$((retry_count + 1))
        echo -n "."
        sleep 2
    done
    
    echo ""
    log_error "MySQL 服务启动超时"
    return 1
}

# 检查 MySQL 端口映射
check_mysql_port() {
    log_info "检查 MySQL 端口映射..."
    
    # 检查 docker-compose.yml 中是否启用了端口映射
    if grep -q "^[[:space:]]*#[[:space:]]*-[[:space:]]*\"3306:3306\"" "$COMPOSE_FILE"; then
        log_warning "MySQL 端口未映射到主机"
        echo "需要启用端口映射才能从主机连接 MySQL"
        echo "请编辑 docker-compose.yml，取消注释以下行:"
        echo "  ports:"
        echo "    - \"3306:3306\""
        echo ""
        read -p "是否自动启用端口映射? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            enable_mysql_port
        else
            log_info "使用容器内连接方式"
            MYSQL_DSN="root:123456@tcp(mysql:3306)/new-api"
        fi
    else
        log_success "MySQL 端口已映射到主机"
    fi
}

# 启用 MySQL 端口映射
enable_mysql_port() {
    log_info "启用 MySQL 端口映射..."
    
    # 备份原文件
    cp "$COMPOSE_FILE" "${COMPOSE_FILE}.backup"
    
    # 取消注释端口映射
    sed -i 's/^[[:space:]]*#[[:space:]]*ports:/    ports:/' "$COMPOSE_FILE"
    sed -i 's/^[[:space:]]*#[[:space:]]*-[[:space:]]*"3306:3306"/      - "3306:3306"/' "$COMPOSE_FILE"
    
    log_success "已启用 MySQL 端口映射"
    log_warning "需要重启服务以应用更改:"
    echo "  cd .. && docker-compose down && docker-compose up -d"
}

# 测试数据库连接
test_connection() {
    log_info "测试数据库连接..."
    
    go run channel_manager.go -action=export -dry-run -verbose -output=/dev/null 2>&1 | grep -q "找到.*个渠道"
    
    if [ $? -eq 0 ]; then
        log_success "数据库连接成功"
        return 0
    else
        log_error "数据库连接失败"
        echo "请检查:"
        echo "  1. MySQL 服务是否正在运行"
        echo "  2. 端口映射是否正确"
        echo "  3. 数据库连接字符串是否正确"
        return 1
    fi
}

# 导出渠道数据
export_channels() {
    local format="${1:-json}"
    local output="$2"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    if [ -z "$output" ]; then
        output="channels_export_${timestamp}.${format}"
    fi
    
    log_info "导出渠道数据为 $format 格式..."
    
    if go run channel_manager.go -action=export -format="$format" -output="$output" -dsn="$MYSQL_DSN" -verbose; then
        log_success "渠道数据已导出到: $output"
    else
        log_error "导出失败"
        return 1
    fi
}

# 备份渠道数据
backup_channels() {
    local output="$1"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    if [ -z "$output" ]; then
        output="channels_backup_${timestamp}.json"
    fi
    
    log_info "备份渠道数据..."
    
    if go run channel_manager.go -action=backup -output="$output" -dsn="$MYSQL_DSN" -verbose; then
        log_success "渠道数据已备份到: $output"
    else
        log_error "备份失败"
        return 1
    fi
}

# 导入渠道数据
import_channels() {
    local input="$1"
    local mode="${2:-skip}"  # skip, update
    
    if [ -z "$input" ]; then
        log_error "请指定要导入的文件"
        return 1
    fi
    
    if [ ! -f "$input" ]; then
        log_error "文件不存在: $input"
        return 1
    fi
    
    log_info "导入渠道数据从: $input"
    
    local import_flags=""
    if [ "$mode" = "update" ]; then
        import_flags="-update-existing"
        log_warning "将更新已存在的渠道"
    else
        import_flags="-skip-existing"
        log_info "将跳过已存在的渠道"
    fi
    
    # 先进行模拟运行
    log_info "执行模拟导入..."
    if go run channel_manager.go -action=import -input="$input" $import_flags -dsn="$MYSQL_DSN" -dry-run; then
        echo ""
        read -p "确认执行实际导入? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "执行实际导入..."
            if go run channel_manager.go -action=import -input="$input" $import_flags -dsn="$MYSQL_DSN" -verbose; then
                log_success "导入完成"
            else
                log_error "导入失败"
                return 1
            fi
        else
            log_info "取消导入"
        fi
    else
        log_error "模拟导入失败"
        return 1
    fi
}

# 恢复渠道数据
restore_channels() {
    local input="$1"
    
    if [ -z "$input" ]; then
        log_error "请指定要恢复的备份文件"
        return 1
    fi
    
    if [ ! -f "$input" ]; then
        log_error "备份文件不存在: $input"
        return 1
    fi
    
    log_warning "⚠️  恢复操作将删除所有现有渠道数据!"
    echo "备份文件: $input"
    echo ""
    read -p "确认执行恢复操作? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "执行恢复操作..."
        if go run channel_manager.go -action=restore -input="$input" -dsn="$MYSQL_DSN" -verbose; then
            log_success "恢复完成"
        else
            log_error "恢复失败"
            return 1
        fi
    else
        log_info "取消恢复"
    fi
}

# 显示帮助信息
show_help() {
    cat << EOF
Docker Compose 渠道管理助手

用法: $0 [命令] [选项]

命令:
  check       检查 Docker 服务状态和连接
  export      导出渠道数据
  backup      备份渠道数据（完整备份）
  import      导入渠道数据
  restore     恢复渠道数据（删除现有数据）
  help        显示此帮助信息

导出选项:
  export [格式] [输出文件]
  格式: json, csv, txt (默认: json)
  
  示例:
    $0 export json
    $0 export csv channels.csv
    $0 export txt report.txt

备份选项:
  backup [输出文件]
  
  示例:
    $0 backup
    $0 backup my_backup.json

导入选项:
  import <文件> [模式]
  模式: skip (跳过重复), update (更新重复) (默认: skip)
  
  示例:
    $0 import channels.json
    $0 import channels.json update

恢复选项:
  restore <备份文件>
  
  示例:
    $0 restore backup.json

环境要求:
  - Docker 和 Docker Compose 已安装
  - MySQL 服务在 Docker Compose 中运行
  - Go 运行环境
EOF
}

# 主函数
main() {
    local command="$1"
    
    case "$command" in
        "check")
            check_services && wait_for_mysql && test_connection
            ;;
        "export")
            check_services && wait_for_mysql && export_channels "$2" "$3"
            ;;
        "backup")
            check_services && wait_for_mysql && backup_channels "$2"
            ;;
        "import")
            check_services && wait_for_mysql && import_channels "$2" "$3"
            ;;
        "restore")
            check_services && wait_for_mysql && restore_channels "$2"
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        "")
            echo "请指定命令。使用 '$0 help' 查看帮助。"
            ;;
        *)
            log_error "未知命令: $command"
            echo "使用 '$0 help' 查看可用命令。"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"