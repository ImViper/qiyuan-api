#!/bin/bash

# 渠道导出快速运行脚本
# 使用方法: ./run_export.sh [格式] [输出文件]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 默认参数
FORMAT="${1:-json}"
OUTPUT_FILE="${2:-}"
VERBOSE=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -f|--format)
            FORMAT="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            echo "使用方法: $0 [选项]"
            echo "选项:"
            echo "  -f, --format FORMAT    输出格式 (json, csv, txt)"
            echo "  -o, --output FILE      输出文件"
            echo "  -v, --verbose          显示详细信息"
            echo "  -h, --help             显示帮助"
            echo ""
            echo "示例:"
            echo "  $0                     # 导出为JSON"
            echo "  $0 -f csv             # 导出为CSV"
            echo "  $0 -f txt -o report.txt # 导出为文本文件"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# 构建命令
CMD="go run export_channels.go -format $FORMAT"

if [ -n "$OUTPUT_FILE" ]; then
    CMD="$CMD -output $OUTPUT_FILE"
fi

if [ "$VERBOSE" = true ]; then
    CMD="$CMD -verbose"
fi

echo "正在导出渠道数据..."
echo "执行命令: $CMD"

# 执行导出
eval $CMD

if [ $? -eq 0 ]; then
    echo "✅ 导出完成！"
else
    echo "❌ 导出失败！"
    exit 1
fi