#!/bin/bash

# 数据库重置脚本 - 包含完整备份和安全恢复选项
# 用于安全地重置渠道数据库内容

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 配置
MYSQL_DSN="root:123456@tcp(localhost:3306)/new-api"
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 显示帮助
show_help() {
    cat << EOF
数据库重置工具

用法: $0 [选项]

选项:
  --backup-only       仅创建备份，不重置数据库
  --reset-only        仅重置数据库，不创建备份（危险操作）
  --restore FILE      从指定备份文件恢复数据库
  --dry-run           模拟运行，显示将要执行的操作
  --backup-dir DIR    指定备份目录 (默认: ./backups)
  --verbose           显示详细信息
  --help              显示此帮助信息

安全重置流程:
  1. 自动创建完整备份
  2. 确认重置操作
  3. 清空渠道数据
  4. 提供恢复选项

示例:
  $0                           # 完整的备份+重置流程
  $0 --backup-only             # 仅创建备份
  $0 --restore backup.json     # 从备份恢复
  $0 --dry-run                 # 模拟运行
EOF
}

# 检查依赖
check_dependencies() {
    if ! command -v go &> /dev/null; then
        log_error "Go 运行环境未找到"
        return 1
    fi
    
    if ! go list -m github.com/glebarez/sqlite &> /dev/null; then
        log_warning "正在安装依赖..."
        go mod tidy
    fi
    
    return 0
}

# 创建备份目录
create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_info "创建备份目录: $BACKUP_DIR"
    fi
}

# 创建完整备份
create_backup() {
    local backup_file="$BACKUP_DIR/reset_backup_${TIMESTAMP}.json"
    
    log_info "创建数据库备份..."
    
    if go run channel_manager.go -action=backup -output="$backup_file" -dsn="$MYSQL_DSN" -verbose; then
        log_success "备份已创建: $backup_file"
        echo "备份文件: $backup_file"
        return 0
    else
        log_error "备份创建失败"
        return 1
    fi
}

# 统计当前数据
count_current_data() {
    log_info "统计当前数据库内容..."
    
    local temp_export="/tmp/count_export_$$.json"
    
    if go run channel_manager.go -action=export -output="$temp_export" -dsn="$MYSQL_DSN" 2>/dev/null; then
        local count=$(grep -o '"total_channels":[0-9]*' "$temp_export" | cut -d':' -f2)
        echo "当前渠道数量: $count"
        rm -f "$temp_export"
        return 0
    else
        log_warning "无法统计当前数据"
        return 1
    fi
}

# 重置数据库
reset_database() {
    log_warning "⚠️  即将清空所有渠道数据!"
    echo "此操作不可逆转，请确保已创建备份"
    echo ""
    
    read -p "确认重置数据库? 输入 'RESET' 确认: " -r
    
    if [ "$REPLY" != "RESET" ]; then
        log_info "取消重置操作"
        return 1
    fi
    
    log_info "正在重置数据库..."
    
    # 使用 restore 操作清空数据库（传入空的备份文件）
    local empty_backup="/tmp/empty_backup_$$.json"
    cat > "$empty_backup" << EOF
{
  "export_time": "$(date '+%Y-%m-%d %H:%M:%S')",
  "export_version": "1.0.0",
  "total_channels": 0,
  "database_info": "Reset Operation",
  "channels": []
}
EOF
    
    if go run channel_manager.go -action=restore -input="$empty_backup" -dsn="$MYSQL_DSN"; then
        log_success "数据库已重置"
        rm -f "$empty_backup"
        return 0
    else
        log_error "数据库重置失败"
        rm -f "$empty_backup"
        return 1
    fi
}

# 恢复数据库
restore_database() {
    local restore_file="$1"
    
    if [ ! -f "$restore_file" ]; then
        log_error "备份文件不存在: $restore_file"
        return 1
    fi
    
    log_info "从备份文件恢复: $restore_file"
    
    # 显示备份文件信息
    local backup_info=$(grep -E '"export_time"|"total_channels"' "$restore_file" | head -2)
    echo "备份信息:"
    echo "$backup_info"
    echo ""
    
    read -p "确认从此备份恢复? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if go run channel_manager.go -action=restore -input="$restore_file" -dsn="$MYSQL_DSN" -verbose; then
            log_success "数据库恢复完成"
            return 0
        else
            log_error "数据库恢复失败"
            return 1
        fi
    else
        log_info "取消恢复操作"
        return 1
    fi
}

# 列出可用备份
list_backups() {
    if [ -d "$BACKUP_DIR" ]; then
        echo "可用备份文件:"
        ls -la "$BACKUP_DIR"/*.json 2>/dev/null | while read -r line; do
            echo "  $line"
        done
    else
        echo "无备份文件"
    fi
}

# 主函数
main() {
    local backup_only=false
    local reset_only=false
    local restore_file=""
    local dry_run=false
    local verbose=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --backup-only)
                backup_only=true
                shift
                ;;
            --reset-only)
                reset_only=true
                shift
                ;;
            --restore)
                restore_file="$2"
                shift 2
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --backup-dir)
                BACKUP_DIR="$2"
                shift 2
                ;;
            --verbose)
                verbose=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 检查依赖
    if ! check_dependencies; then
        exit 1
    fi
    
    # 创建备份目录
    create_backup_dir
    
    # 如果指定了恢复文件
    if [ -n "$restore_file" ]; then
        restore_database "$restore_file"
        exit $?
    fi
    
    # 显示当前状态
    count_current_data
    echo ""
    
    # 模拟运行
    if [ "$dry_run" = true ]; then
        echo "=== 模拟运行 ==="
        echo "将要执行的操作:"
        if [ "$backup_only" != true ]; then
            echo "1. 创建备份到: $BACKUP_DIR/reset_backup_${TIMESTAMP}.json"
        fi
        if [ "$reset_only" != true ] && [ "$backup_only" != true ]; then
            echo "2. 重置数据库（清空所有渠道）"
        fi
        echo "=== 模拟结束 ==="
        exit 0
    fi
    
    # 仅备份模式
    if [ "$backup_only" = true ]; then
        create_backup
        exit $?
    fi
    
    # 仅重置模式（危险）
    if [ "$reset_only" = true ]; then
        log_warning "⚠️  危险模式：仅重置，不创建备份"
        reset_database
        exit $?
    fi
    
    # 完整流程：备份 + 重置
    log_info "开始完整的数据库重置流程"
    echo "步骤 1: 创建备份"
    
    if create_backup; then
        echo ""
        echo "步骤 2: 重置数据库"
        
        if reset_database; then
            echo ""
            log_success "数据库重置完成"
            echo ""
            echo "备份文件位置: $BACKUP_DIR/"
            echo "如需恢复，请使用: $0 --restore <备份文件>"
            echo ""
            list_backups
        else
            log_error "重置失败，数据未被修改"
            exit 1
        fi
    else
        log_error "备份失败，中止重置操作"
        exit 1
    fi
}

# 执行主函数
main "$@"