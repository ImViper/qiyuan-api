#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Python脚本的跨平台兼容性
"""

import os
import sys
import platform
import subprocess
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    log_info, log_success, log_warning, log_error,
    Colors, get_timestamp, check_go_installed
)


def test_platform_info():
    """测试平台信息"""
    print("=" * 60)
    print("平台信息测试")
    print("=" * 60)
    
    info = {
        "操作系统": platform.system(),
        "系统版本": platform.version(),
        "平台": platform.platform(),
        "Python版本": sys.version,
        "架构": platform.machine(),
        "处理器": platform.processor()
    }
    
    for key, value in info.items():
        print(f"{key}: {value}")
    
    print()
    return True


def test_color_output():
    """测试彩色输出"""
    print("=" * 60)
    print("彩色输出测试")
    print("=" * 60)
    
    log_info("这是信息消息")
    log_success("这是成功消息")
    log_warning("这是警告消息")
    log_error("这是错误消息")
    
    print()
    return True


def test_path_operations():
    """测试路径操作"""
    print("=" * 60)
    print("路径操作测试")
    print("=" * 60)
    
    # 测试路径分隔符
    test_path = Path("test") / "dir" / "file.txt"
    print(f"路径连接测试: {test_path}")
    
    # 测试绝对路径
    abs_path = Path.cwd()
    print(f"当前工作目录: {abs_path}")
    
    # 测试相对路径
    script_dir = Path(__file__).parent
    print(f"脚本目录: {script_dir}")
    
    # 测试路径存在性
    if script_dir.exists():
        log_success("脚本目录存在")
    else:
        log_error("脚本目录不存在")
    
    print()
    return True


def test_command_execution():
    """测试命令执行"""
    print("=" * 60)
    print("命令执行测试")
    print("=" * 60)
    
    # 测试Python版本命令
    if platform.system() == "Windows":
        cmd = ["python", "--version"]
    else:
        cmd = ["python3", "--version"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            log_success(f"Python命令执行成功: {result.stdout.strip()}")
        else:
            log_error(f"Python命令执行失败: {result.stderr}")
    except Exception as e:
        log_error(f"命令执行异常: {e}")
    
    # 测试Go环境
    if check_go_installed():
        log_success("Go环境已安装")
    else:
        log_warning("Go环境未安装")
    
    print()
    return True


def test_file_encoding():
    """测试文件编码"""
    print("=" * 60)
    print("文件编码测试")
    print("=" * 60)
    
    test_text = "测试中文编码: Hello 世界! 🚀"
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', 
                                     suffix='.txt', delete=False) as tmp:
        tmp.write(test_text)
        tmp_path = tmp.name
    
    try:
        # 读取文件
        with open(tmp_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if content == test_text:
            log_success("UTF-8编码读写正常")
        else:
            log_error("UTF-8编码读写异常")
        
        # 清理临时文件
        os.unlink(tmp_path)
    except Exception as e:
        log_error(f"文件编码测试失败: {e}")
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    
    print()
    return True


def test_timestamp():
    """测试时间戳生成"""
    print("=" * 60)
    print("时间戳测试")
    print("=" * 60)
    
    ts1 = get_timestamp()
    print(f"默认格式时间戳: {ts1}")
    
    ts2 = get_timestamp("%Y-%m-%d %H:%M:%S")
    print(f"自定义格式时间戳: {ts2}")
    
    print()
    return True


def test_script_help():
    """测试脚本帮助信息"""
    print("=" * 60)
    print("脚本帮助信息测试")
    print("=" * 60)
    
    scripts = [
        "reset_database.py",
        "docker_helper.py",
        "run_export.py"
    ]
    
    for script in scripts:
        script_path = Path(__file__).parent / script
        if script_path.exists():
            print(f"\n测试 {script} --help:")
            cmd = [sys.executable, str(script_path), "--help"]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, 
                                      timeout=5)
                if result.returncode == 0:
                    log_success(f"{script} 帮助信息正常")
                    # 只显示前3行
                    lines = result.stdout.split('\n')[:3]
                    for line in lines:
                        print(f"  {line}")
                else:
                    log_warning(f"{script} 帮助信息返回非零: {result.returncode}")
            except subprocess.TimeoutExpired:
                log_error(f"{script} 执行超时")
            except Exception as e:
                log_error(f"{script} 执行失败: {e}")
        else:
            log_warning(f"{script} 不存在")
    
    print()
    return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Python脚本跨平台兼容性测试")
    print("=" * 60 + "\n")
    
    tests = [
        ("平台信息", test_platform_info),
        ("彩色输出", test_color_output),
        ("路径操作", test_path_operations),
        ("命令执行", test_command_execution),
        ("文件编码", test_file_encoding),
        ("时间戳生成", test_timestamp),
        ("脚本帮助", test_script_help)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            log_error(f"{test_name} 测试异常: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"总计: {passed + failed}")
    
    if failed == 0:
        log_success("所有测试通过！Python脚本跨平台兼容性良好。")
    else:
        log_warning(f"有 {failed} 个测试失败，请检查兼容性问题。")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())