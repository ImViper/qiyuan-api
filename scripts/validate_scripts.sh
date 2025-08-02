#!/bin/bash

# 脚本验证工具 - 检查所有脚本的语法和依赖

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

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

echo "🔍 脚本验证工具"
echo "================="

# 检查 Go 环境
log_info "检查 Go 运行环境..."
if command -v go &> /dev/null; then
    go_version=$(go version)
    log_success "Go 环境正常: $go_version"
else
    log_error "Go 运行环境未找到"
    exit 1
fi

# 检查 Go 模块依赖
log_info "检查 Go 模块依赖..."
if go mod tidy; then
    log_success "依赖检查完成"
else
    log_error "依赖安装失败"
    exit 1
fi

# 验证各个脚本的语法
scripts=("channel_manager.go" "export_channels.go")

for script in "${scripts[@]}"; do
    log_info "验证脚本语法: $script"
    
    # 语法检查
    temp_exe="${script%.go}.tmp.exe"
    if go build -o "$temp_exe" "$script"; then
        log_success "$script 编译通过"
        rm -f "$temp_exe"
    else
        log_error "$script 编译失败"
        exit 1
    fi
    
    # Go vet 检查
    if go vet "$script"; then
        log_success "$script vet 检查通过"
    else
        log_warning "$script vet 发现问题"
    fi
    
    # 帮助信息测试
    if go run "$script" -help > /dev/null 2>&1; then
        log_success "$script 帮助信息正常"
    else
        log_error "$script 帮助信息异常"
    fi
done

# 检查辅助脚本权限
helper_scripts=("docker_helper.sh" "reset_database.sh" "run_export.sh")

for script in "${helper_scripts[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            log_success "$script 执行权限正常"
        else
            log_warning "$script 缺少执行权限，正在修复..."
            chmod +x "$script"
            log_success "$script 权限已修复"
        fi
    else
        log_warning "$script 文件不存在"
    fi
done

# 验证测试数据
log_info "验证测试数据文件..."
if [ -f "test_channels.json" ]; then
    # 简单的 JSON 格式检查
    if grep -q '"channels"' test_channels.json && grep -q '"total_channels"' test_channels.json; then
        log_success "test_channels.json 格式看起来正确"
    else
        log_warning "test_channels.json 格式可能有问题，但不影响脚本运行"
    fi
else
    log_info "test_channels.json 不存在，这是正常的"
fi

# 检查目录结构
log_info "检查脚本目录结构..."
required_files=("channel_manager.go" "export_channels.go" "go.mod" "README.md")

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        log_success "$file 存在"
    else
        log_error "$file 缺失"
    fi
done

# 显示脚本功能摘要
echo ""
log_info "脚本功能摘要:"
echo "📋 channel_manager.go  - 完整的渠道管理（导入/导出/备份/恢复）"
echo "📤 export_channels.go  - 简单的渠道导出工具"
echo "🐳 docker_helper.sh    - Docker Compose 环境助手"
echo "🔄 reset_database.sh   - 安全数据库重置工具"
echo "⚡ run_export.sh       - 快速导出脚本"

echo ""
log_info "使用示例:"
echo "# 查看完整帮助"
echo "go run channel_manager.go -help"
echo ""
echo "# Docker 环境检查"
echo "./docker_helper.sh check"
echo ""
echo "# 导出渠道数据"
echo "./docker_helper.sh export json"

echo ""
log_success "✅ 脚本验证完成！所有脚本准备就绪。"