@echo off
setlocal enabledelayedexpansion

REM Docker Compose 渠道管理助手脚本 (Windows)

cd /d "%~dp0"

set MYSQL_DSN=root:123456@tcp(localhost:3306)/new-api
set MYSQL_CONTAINER=mysql
set COMPOSE_FILE=..\docker-compose.yml

if "%~1"=="" (
    echo 请指定命令。使用 "%~nx0 help" 查看帮助。
    exit /b 1
)

if "%~1"=="help" goto help
if "%~1"=="--help" goto help
if "%~1"=="-h" goto help
if "%~1"=="check" goto check
if "%~1"=="export" goto export
if "%~1"=="backup" goto backup
if "%~1"=="import" goto import
if "%~1"=="restore" goto restore

echo [ERROR] 未知命令: %~1
echo 使用 "%~nx0 help" 查看可用命令。
exit /b 1

:help
echo.
echo Docker Compose 渠道管理助手
echo.
echo 用法: %~nx0 [命令] [选项]
echo.
echo 命令:
echo   check       检查 Docker 服务状态和连接
echo   export      导出渠道数据
echo   backup      备份渠道数据（完整备份）
echo   import      导入渠道数据
echo   restore     恢复渠道数据（删除现有数据）
echo   help        显示此帮助信息
echo.
echo 导出选项:
echo   export [格式] [输出文件]
echo   格式: json, csv, txt (默认: json)
echo.
echo   示例:
echo     %~nx0 export json
echo     %~nx0 export csv channels.csv
echo     %~nx0 export txt report.txt
echo.
echo 备份选项:
echo   backup [输出文件]
echo.
echo   示例:
echo     %~nx0 backup
echo     %~nx0 backup my_backup.json
echo.
echo 导入选项:
echo   import ^<文件^> [模式]
echo   模式: skip (跳过重复), update (更新重复) (默认: skip)
echo.
echo   示例:
echo     %~nx0 import channels.json
echo     %~nx0 import channels.json update
echo.
echo 恢复选项:
echo   restore ^<备份文件^>
echo.
echo   示例:
echo     %~nx0 restore backup.json
echo.
exit /b 0

:check
echo [INFO] 检查 Docker Compose 服务状态...

docker-compose -f "%COMPOSE_FILE%" ps | findstr "mysql.*Up" >nul
if !errorlevel! neq 0 (
    echo [ERROR] MySQL 服务未运行
    echo 请先启动 Docker Compose 服务:
    echo   cd .. ^&^& docker-compose up -d
    exit /b 1
)

echo [SUCCESS] MySQL 服务正在运行

echo [INFO] 测试数据库连接...
go run channel_manager.go -action=export -dry-run -verbose -output=nul 2>nul | findstr "找到.*个渠道" >nul

if !errorlevel! equ 0 (
    echo [SUCCESS] 数据库连接成功
) else (
    echo [ERROR] 数据库连接失败
    echo 请检查:
    echo   1. MySQL 服务是否正在运行
    echo   2. 端口映射是否正确
    echo   3. 数据库连接字符串是否正确
    exit /b 1
)
exit /b 0

:export
set FORMAT=%~2
set OUTPUT=%~3

if "%FORMAT%"=="" set FORMAT=json

if "%OUTPUT%"=="" (
    for /f "tokens=2 delims==" %%i in ('wmic OS Get localdatetime /value') do set datetime=%%i
    set timestamp=!datetime:~0,8!_!datetime:~8,6!
    set OUTPUT=channels_export_!timestamp!.!FORMAT!
)

echo [INFO] 导出渠道数据为 %FORMAT% 格式...

go run channel_manager.go -action=export -format="%FORMAT%" -output="%OUTPUT%" -dsn="%MYSQL_DSN%" -verbose

if !errorlevel! equ 0 (
    echo [SUCCESS] 渠道数据已导出到: %OUTPUT%
) else (
    echo [ERROR] 导出失败
    exit /b 1
)
exit /b 0

:backup
set OUTPUT=%~2

if "%OUTPUT%"=="" (
    for /f "tokens=2 delims==" %%i in ('wmic OS Get localdatetime /value') do set datetime=%%i
    set timestamp=!datetime:~0,8!_!datetime:~8,6!
    set OUTPUT=channels_backup_!timestamp!.json
)

echo [INFO] 备份渠道数据...

go run channel_manager.go -action=backup -output="%OUTPUT%" -dsn="%MYSQL_DSN%" -verbose

if !errorlevel! equ 0 (
    echo [SUCCESS] 渠道数据已备份到: %OUTPUT%
) else (
    echo [ERROR] 备份失败
    exit /b 1
)
exit /b 0

:import
set INPUT=%~2
set MODE=%~3

if "%INPUT%"=="" (
    echo [ERROR] 请指定要导入的文件
    exit /b 1
)

if not exist "%INPUT%" (
    echo [ERROR] 文件不存在: %INPUT%
    exit /b 1
)

if "%MODE%"=="" set MODE=skip

echo [INFO] 导入渠道数据从: %INPUT%

set IMPORT_FLAGS=-skip-existing
if "%MODE%"=="update" (
    set IMPORT_FLAGS=-update-existing
    echo [WARNING] 将更新已存在的渠道
) else (
    echo [INFO] 将跳过已存在的渠道
)

echo [INFO] 执行模拟导入...
go run channel_manager.go -action=import -input="%INPUT%" %IMPORT_FLAGS% -dsn="%MYSQL_DSN%" -dry-run

if !errorlevel! equ 0 (
    echo.
    set /p "confirm=确认执行实际导入? (y/n): "
    if /i "!confirm!"=="y" (
        echo [INFO] 执行实际导入...
        go run channel_manager.go -action=import -input="%INPUT%" %IMPORT_FLAGS% -dsn="%MYSQL_DSN%" -verbose
        if !errorlevel! equ 0 (
            echo [SUCCESS] 导入完成
        ) else (
            echo [ERROR] 导入失败
            exit /b 1
        )
    ) else (
        echo [INFO] 取消导入
    )
) else (
    echo [ERROR] 模拟导入失败
    exit /b 1
)
exit /b 0

:restore
set INPUT=%~2

if "%INPUT%"=="" (
    echo [ERROR] 请指定要恢复的备份文件
    exit /b 1
)

if not exist "%INPUT%" (
    echo [ERROR] 备份文件不存在: %INPUT%
    exit /b 1
)

echo [WARNING] ⚠️  恢复操作将删除所有现有渠道数据!
echo 备份文件: %INPUT%
echo.
set /p "confirm=确认执行恢复操作? (y/n): "

if /i "!confirm!"=="y" (
    echo [INFO] 执行恢复操作...
    go run channel_manager.go -action=restore -input="%INPUT%" -dsn="%MYSQL_DSN%" -verbose
    if !errorlevel! equ 0 (
        echo [SUCCESS] 恢复完成
    ) else (
        echo [ERROR] 恢复失败
        exit /b 1
    )
) else (
    echo [INFO] 取消恢复
)
exit /b 0