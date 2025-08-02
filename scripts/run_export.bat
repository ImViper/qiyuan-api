@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM 渠道导出快速运行脚本 (Windows)
REM 使用方法: run_export.bat [格式] [输出文件]

cd /d "%~dp0"

REM 默认参数
set FORMAT=json
set OUTPUT_FILE=
set VERBOSE=false

REM 解析参数
:parse_args
if "%~1"=="" goto run_export
if "%~1"=="-f" (
    set FORMAT=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--format" (
    set FORMAT=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="-o" (
    set OUTPUT_FILE=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--output" (
    set OUTPUT_FILE=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="-v" (
    set VERBOSE=true
    shift
    goto parse_args
)
if "%~1"=="--verbose" (
    set VERBOSE=true
    shift
    goto parse_args
)
if "%~1"=="-h" goto help
if "%~1"=="--help" goto help

echo 未知参数: %~1
exit /b 1

:help
echo 使用方法: %~nx0 [选项]
echo 选项:
echo   -f, --format FORMAT    输出格式 (json, csv, txt)
echo   -o, --output FILE      输出文件
echo   -v, --verbose          显示详细信息
echo   -h, --help             显示帮助
echo.
echo 示例:
echo   %~nx0                     # 导出为JSON
echo   %~nx0 -f csv             # 导出为CSV  
echo   %~nx0 -f txt -o report.txt # 导出为文本文件
exit /b 0

:run_export
REM 构建命令
set CMD=go run export_channels.go -format %FORMAT%

if not "%OUTPUT_FILE%"=="" (
    set CMD=!CMD! -output "%OUTPUT_FILE%"
)

if "%VERBOSE%"=="true" (
    set CMD=!CMD! -verbose
)

echo 正在导出渠道数据...
echo 执行命令: !CMD!

REM 执行导出
!CMD!

if !errorlevel! equ 0 (
    echo ✅ 导出完成！
) else (
    echo ❌ 导出失败！
    exit /b 1
)

pause