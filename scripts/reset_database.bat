@echo off
setlocal enabledelayedexpansion

REM 数据库重置脚本 - Windows 版本
REM 包含完整备份和安全恢复选项

cd /d "%~dp0"

set MYSQL_DSN=root:123456@tcp(localhost:3306)/new-api
set BACKUP_DIR=.\backups

REM 获取时间戳
for /f "tokens=2 delims==" %%i in ('wmic OS Get localdatetime /value') do set datetime=%%i
set TIMESTAMP=!datetime:~0,8!_!datetime:~8,6!

REM 解析参数
set BACKUP_ONLY=false
set RESET_ONLY=false
set RESTORE_FILE=
set DRY_RUN=false
set VERBOSE=false

:parse_args
if "%~1"=="" goto main
if "%~1"=="--backup-only" (
    set BACKUP_ONLY=true
    shift
    goto parse_args
)
if "%~1"=="--reset-only" (
    set RESET_ONLY=true
    shift
    goto parse_args
)
if "%~1"=="--restore" (
    set RESTORE_FILE=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--dry-run" (
    set DRY_RUN=true
    shift
    goto parse_args
)
if "%~1"=="--backup-dir" (
    set BACKUP_DIR=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--verbose" (
    set VERBOSE=true
    shift
    goto parse_args
)
if "%~1"=="--help" goto help

echo [ERROR] 未知参数: %~1
goto help

:help
echo.
echo 数据库重置工具
echo.
echo 用法: %~nx0 [选项]
echo.
echo 选项:
echo   --backup-only       仅创建备份，不重置数据库
echo   --reset-only        仅重置数据库，不创建备份（危险操作）
echo   --restore FILE      从指定备份文件恢复数据库
echo   --dry-run           模拟运行，显示将要执行的操作
echo   --backup-dir DIR    指定备份目录 (默认: .\backups)
echo   --verbose           显示详细信息
echo   --help              显示此帮助信息
echo.
echo 安全重置流程:
echo   1. 自动创建完整备份
echo   2. 确认重置操作
echo   3. 清空渠道数据
echo   4. 提供恢复选项
echo.
echo 示例:
echo   %~nx0                           # 完整的备份+重置流程
echo   %~nx0 --backup-only             # 仅创建备份
echo   %~nx0 --restore backup.json     # 从备份恢复
echo   %~nx0 --dry-run                 # 模拟运行
echo.
exit /b 0

:main
REM 检查依赖
where go >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] Go 运行环境未找到
    exit /b 1
)

REM 创建备份目录
if not exist "%BACKUP_DIR%" (
    mkdir "%BACKUP_DIR%"
    echo [INFO] 创建备份目录: %BACKUP_DIR%
)

REM 如果指定了恢复文件
if not "%RESTORE_FILE%"=="" (
    call :restore_database "%RESTORE_FILE%"
    exit /b !errorlevel!
)

REM 统计当前数据
call :count_current_data

REM 模拟运行
if "%DRY_RUN%"=="true" (
    echo === 模拟运行 ===
    echo 将要执行的操作:
    if "%BACKUP_ONLY%" neq "true" (
        echo 1. 创建备份到: %BACKUP_DIR%\reset_backup_!TIMESTAMP!.json
    )
    if "%RESET_ONLY%" neq "true" if "%BACKUP_ONLY%" neq "true" (
        echo 2. 重置数据库（清空所有渠道）
    )
    echo === 模拟结束 ===
    exit /b 0
)

REM 仅备份模式
if "%BACKUP_ONLY%"=="true" (
    call :create_backup
    exit /b !errorlevel!
)

REM 仅重置模式（危险）
if "%RESET_ONLY%"=="true" (
    echo [WARNING] ⚠️  危险模式：仅重置，不创建备份
    call :reset_database
    exit /b !errorlevel!
)

REM 完整流程：备份 + 重置
echo [INFO] 开始完整的数据库重置流程
echo 步骤 1: 创建备份

call :create_backup
if !errorlevel! equ 0 (
    echo.
    echo 步骤 2: 重置数据库
    
    call :reset_database
    if !errorlevel! equ 0 (
        echo.
        echo [SUCCESS] 数据库重置完成
        echo.
        echo 备份文件位置: %BACKUP_DIR%\
        echo 如需恢复，请使用: %~nx0 --restore ^<备份文件^>
        echo.
        call :list_backups
    ) else (
        echo [ERROR] 重置失败，数据未被修改
        exit /b 1
    )
) else (
    echo [ERROR] 备份失败，中止重置操作
    exit /b 1
)

exit /b 0

:create_backup
set backup_file=%BACKUP_DIR%\reset_backup_%TIMESTAMP%.json

echo [INFO] 创建数据库备份...

go run channel_manager.go -action=backup -output="%backup_file%" -dsn="%MYSQL_DSN%" -verbose

if !errorlevel! equ 0 (
    echo [SUCCESS] 备份已创建: %backup_file%
    echo 备份文件: %backup_file%
) else (
    echo [ERROR] 备份创建失败
)
exit /b !errorlevel!

:count_current_data
echo [INFO] 统计当前数据库内容...

set temp_export=%TEMP%\count_export_%RANDOM%.json

go run channel_manager.go -action=export -output="%temp_export%" -dsn="%MYSQL_DSN%" >nul 2>&1

if !errorlevel! equ 0 (
    for /f "tokens=2 delims=:" %%i in ('findstr "total_channels" "%temp_export%"') do (
        set count=%%i
        set count=!count:,=!
        set count=!count: =!
        echo 当前渠道数量: !count!
    )
    del "%temp_export%" >nul 2>&1
) else (
    echo [WARNING] 无法统计当前数据
)
exit /b 0

:reset_database
echo [WARNING] ⚠️  即将清空所有渠道数据!
echo 此操作不可逆转，请确保已创建备份
echo.

set /p "confirm=确认重置数据库? 输入 'RESET' 确认: "

if not "!confirm!"=="RESET" (
    echo [INFO] 取消重置操作
    exit /b 1
)

echo [INFO] 正在重置数据库...

REM 创建空的备份文件用于重置
set empty_backup=%TEMP%\empty_backup_%RANDOM%.json

echo { > "%empty_backup%"
echo   "export_time": "%date% %time%", >> "%empty_backup%"
echo   "export_version": "1.0.0", >> "%empty_backup%"
echo   "total_channels": 0, >> "%empty_backup%"
echo   "database_info": "Reset Operation", >> "%empty_backup%"
echo   "channels": [] >> "%empty_backup%"
echo } >> "%empty_backup%"

go run channel_manager.go -action=restore -input="%empty_backup%" -dsn="%MYSQL_DSN%"

if !errorlevel! equ 0 (
    echo [SUCCESS] 数据库已重置
    del "%empty_backup%" >nul 2>&1
) else (
    echo [ERROR] 数据库重置失败
    del "%empty_backup%" >nul 2>&1
)
exit /b !errorlevel!

:restore_database
set restore_file=%~1

if not exist "%restore_file%" (
    echo [ERROR] 备份文件不存在: %restore_file%
    exit /b 1
)

echo [INFO] 从备份文件恢复: %restore_file%

echo 备份信息:
findstr "export_time\|total_channels" "%restore_file%" | head -2
echo.

set /p "confirm=确认从此备份恢复? (y/n): "

if /i "!confirm!"=="y" (
    go run channel_manager.go -action=restore -input="%restore_file%" -dsn="%MYSQL_DSN%" -verbose
    if !errorlevel! equ 0 (
        echo [SUCCESS] 数据库恢复完成
    ) else (
        echo [ERROR] 数据库恢复失败
    )
) else (
    echo [INFO] 取消恢复操作
    exit /b 1
)
exit /b !errorlevel!

:list_backups
if exist "%BACKUP_DIR%\*.json" (
    echo 可用备份文件:
    dir /b "%BACKUP_DIR%\*.json"
) else (
    echo 无备份文件
)
exit /b 0