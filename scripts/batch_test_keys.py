#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量测试API密钥脚本
从数据库导出所有API密钥并批量测试
"""

import os
import sys
import time
import argparse
import requests
from typing import List, Tuple, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    log_info, log_success, log_warning, log_error,
    get_timestamp
)

from export_api_keys import APIKeyExporter


class DatabaseCleaner:
    """数据库清理器 - 用于清理无效的API密钥"""
    
    def __init__(self, host: str = "localhost", port: int = 3306,
                 user: str = "root", password: str = "123456",
                 database: str = "new-api"):
        """初始化清理器"""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        
    def connect_db(self):
        """连接数据库"""
        try:
            import pymysql
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return True
        except Exception as e:
            log_error(f"Failed to connect to database: {e}")
            return False
    
    def remove_invalid_keys(self, invalid_keys: List[str], channel_info: Dict[int, Dict]) -> int:
        """
        从数据库中删除无效的API密钥
        
        Args:
            invalid_keys: 无效的API密钥列表
            channel_info: 渠道信息字典 {channel_id: {'name': '', 'keys': []}}
        
        Returns:
            删除的密钥数量
        """
        if not self.connection:
            if not self.connect_db():
                return 0
        
        removed_count = 0
        
        try:
            with self.connection.cursor() as cursor:
                # 处理每个渠道
                for channel_id, info in channel_info.items():
                    channel_name = info['name']
                    all_keys = info['keys']
                    
                    # 找出这个渠道中的有效密钥（不在无效列表中的）
                    valid_keys = [k for k in all_keys if k not in invalid_keys]
                    
                    if len(valid_keys) < len(all_keys):
                        # 有密钥需要删除
                        removed_from_channel = len(all_keys) - len(valid_keys)
                        
                        if valid_keys:
                            # 还有有效密钥，更新渠道
                            new_keys = '\n'.join(valid_keys)
                            sql = "UPDATE channels SET `key` = %s WHERE id = %s"
                            cursor.execute(sql, (new_keys, channel_id))
                            log_info(f"Channel '{channel_name}' (ID: {channel_id}): Removed {removed_from_channel} invalid keys, {len(valid_keys)} keys remaining")
                        else:
                            # 没有有效密钥了，可以选择禁用渠道或删除所有密钥
                            # 这里选择禁用渠道
                            sql = "UPDATE channels SET status = 2, `key` = '' WHERE id = %s"
                            cursor.execute(sql, (channel_id,))
                            log_warning(f"Channel '{channel_name}' (ID: {channel_id}): All keys invalid, channel disabled")
                        
                        removed_count += removed_from_channel
                
                # 提交更改
                if removed_count > 0:
                    self.connection.commit()
                    log_success(f"Successfully removed {removed_count} invalid keys from database")
                else:
                    log_info("No invalid keys to remove")
                    
        except Exception as e:
            log_error(f"Failed to remove invalid keys: {e}")
            if self.connection:
                self.connection.rollback()
            removed_count = 0
        
        return removed_count
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None


def test_gemini_key(api_key: str, model: str = "gemini-2.5-flash", timeout: int = 10) -> Tuple[bool, str, float]:
    """
    测试单个Gemini API密钥
    
    Args:
        api_key: API密钥
        model: 测试模型
        timeout: 超时时间
    
    Returns:
        (是否成功, 消息, 响应时间毫秒)
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": "Say 'OK' in one word."
            }]
        }],
        "generationConfig": {
            "maxOutputTokens": 5,
            "temperature": 0.1
        }
    }
    
    headers = {"Content-Type": "application/json"}
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        response_time = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                return True, "Valid", response_time
            else:
                return False, "Invalid response", response_time
                
        elif response.status_code == 400:
            return False, "Bad request (400)", response_time
        elif response.status_code == 403:
            return False, "Forbidden (403)", response_time
        elif response.status_code == 404:
            return False, f"Model not found", response_time
        elif response.status_code == 429:
            return False, "Rate limited (429)", response_time
        else:
            return False, f"HTTP {response.status_code}", response_time
            
    except requests.exceptions.Timeout:
        return False, "Timeout", timeout * 1000
    except requests.exceptions.ConnectionError:
        return False, "Connection error", 0
    except Exception as e:
        return False, f"Error: {str(e)[:30]}", 0


def batch_test_keys(api_keys: List[str], model: str = "gemini-2.5-flash", 
                   max_workers: int = 5, output_file: str = None,
                   channel_info: Dict[int, Dict] = None) -> Tuple[List[dict], Dict[str, List]]:
    """
    批量测试API密钥
    
    Args:
        api_keys: API密钥列表
        model: 测试模型
        max_workers: 最大并发数
        output_file: 结果输出文件
        channel_info: 渠道信息（用于清理功能）
    
    Returns:
        (测试结果列表, {'valid': [有效密钥], 'invalid': [无效密钥]})
    """
    results = []
    valid_keys = []
    invalid_keys = []
    total = len(api_keys)
    
    if total == 0:
        log_warning("No API keys to test")
        return results, {'valid': valid_keys, 'invalid': invalid_keys}
    
    log_info(f"Testing {total} API keys with model: {model}")
    log_info(f"Using {max_workers} concurrent workers")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有测试任务
        future_to_key = {
            executor.submit(test_gemini_key, key, model): (idx, key)
            for idx, key in enumerate(api_keys)
        }
        
        completed = 0
        valid_count = 0
        
        # 处理完成的任务
        for future in as_completed(future_to_key):
            idx, key = future_to_key[future]
            try:
                success, message, response_time = future.result()
                completed += 1
                
                if success:
                    valid_count += 1
                    valid_keys.append(key)
                    status = "[VALID]"
                else:
                    invalid_keys.append(key)
                    status = "[INVALID]"
                
                # 隐藏部分密钥
                masked_key = key[:10] + "..." + key[-4:] if len(key) > 14 else key
                
                result = {
                    'index': idx + 1,
                    'api_key': key,
                    'masked_key': masked_key,
                    'success': success,
                    'message': message,
                    'response_time': response_time
                }
                results.append(result)
                
                # 打印进度
                print(f"[{completed}/{total}] {status} Key #{idx+1} ({masked_key}): {message} ({response_time:.0f}ms)")
                
            except Exception as e:
                completed += 1
                log_error(f"Error testing key #{idx+1}: {e}")
                results.append({
                    'index': idx + 1,
                    'api_key': key,
                    'masked_key': key[:10] + "..." if len(key) > 10 else key,
                    'success': False,
                    'message': f"Test error: {str(e)}",
                    'response_time': 0
                })
    
    # 保存结果到文件
    if output_file:
        save_results(results, output_file)
    
    # 打印摘要
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Total tested: {total}")
    print(f"Valid keys: {valid_count}")
    print(f"Invalid keys: {total - valid_count}")
    print(f"Success rate: {valid_count/total*100:.1f}%")
    
    # 计算平均响应时间
    valid_times = [r['response_time'] for r in results if r['success']]
    if valid_times:
        avg_time = sum(valid_times) / len(valid_times)
        print(f"Average response time: {avg_time:.0f}ms")
    
    return results, {'valid': valid_keys, 'invalid': invalid_keys}


def save_results(results: List[dict], output_file: str):
    """保存测试结果到文件"""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# API Key Test Results\n")
            f.write(f"# Generated at: {get_timestamp('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# Total keys: {len(results)}\n")
            f.write("#" + "=" * 59 + "\n\n")
            
            # 分别保存有效和无效的密钥
            valid_keys = [r for r in results if r['success']]
            invalid_keys = [r for r in results if not r['success']]
            
            if valid_keys:
                f.write(f"# VALID KEYS ({len(valid_keys)})\n")
                f.write("#" + "-" * 59 + "\n")
                for r in valid_keys:
                    f.write(f"# [{r['index']}] Response: {r['response_time']:.0f}ms\n")
                    f.write(f"{r['api_key']}\n")
                f.write("\n")
            
            if invalid_keys:
                f.write(f"# INVALID KEYS ({len(invalid_keys)})\n")
                f.write("#" + "-" * 59 + "\n")
                for r in invalid_keys:
                    f.write(f"# [{r['index']}] Reason: {r['message']}\n")
                    f.write(f"# {r['api_key']}\n")
                f.write("\n")
        
        log_success(f"Results saved to: {output_file}")
    except Exception as e:
        log_error(f"Failed to save results: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Batch Test Gemini API Keys',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script can:
1. Export API keys from database
2. Test them in batch with gemini-2.5-flash model
3. Save results to file
4. Clean invalid keys from database (optional)

Examples:
  # Test all enabled Gemini channels from database
  %(prog)s
  
  # Test with custom model
  %(prog)s --model gemini-2.5-pro
  
  # Test keys from a file
  %(prog)s --from-file api_keys.txt
  
  # Export keys first, then test
  %(prog)s --export-first
  
  # Save test results
  %(prog)s --save-results test_results.txt
  
  # Include disabled channels
  %(prog)s --include-disabled
  
  # Set concurrent workers
  %(prog)s --workers 10
  
  # Clean invalid keys from database after testing
  %(prog)s --clean-invalid
  
  # Clean without confirmation (dangerous!)
  %(prog)s --clean-invalid --no-confirm
        """
    )
    
    # 数据库参数
    parser.add_argument('--host', default='localhost',
                       help='MySQL host (default: localhost)')
    parser.add_argument('--port', type=int, default=3306,
                       help='MySQL port (default: 3306)')
    parser.add_argument('--user', default='root',
                       help='MySQL user (default: root)')
    parser.add_argument('--password', default='123456',
                       help='MySQL password (default: 123456)')
    parser.add_argument('--database', default='new-api',
                       help='Database name (default: new-api)')
    
    # 测试参数
    parser.add_argument('--model', default='gemini-2.5-flash',
                       help='Model to test (default: gemini-2.5-flash)')
    parser.add_argument('--workers', type=int, default=5,
                       help='Concurrent workers (default: 5)')
    parser.add_argument('--include-disabled', action='store_true',
                       help='Include disabled channels')
    
    # 输入输出
    parser.add_argument('--from-file',
                       help='Read API keys from file (one per line)')
    parser.add_argument('--export-first', action='store_true',
                       help='Export keys to file before testing')
    parser.add_argument('--export-file',
                       help='Export keys to this file')
    parser.add_argument('--save-results',
                       help='Save test results to file')
    
    # 清理参数
    parser.add_argument('--clean-invalid', action='store_true',
                       help='Remove invalid API keys from database after testing')
    parser.add_argument('--no-confirm', action='store_true',
                       help='Skip confirmation when cleaning invalid keys')
    
    args = parser.parse_args()
    
    api_keys = []
    
    # 初始化channel_info
    channel_info = {}
    
    # 从文件读取密钥
    if args.from_file:
        try:
            with open(args.from_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        api_keys.append(line)
            log_info(f"Loaded {len(api_keys)} keys from {args.from_file}")
        except Exception as e:
            log_error(f"Failed to read file: {e}")
            return 1
    
    # 从数据库获取密钥
    else:
        try:
            import pymysql
        except ImportError:
            log_error("pymysql required. Install with: pip install pymysql")
            return 1
        
        # 创建导出器
        exporter = APIKeyExporter(
            host=args.host,
            port=args.port,
            user=args.user,
            password=args.password,
            database=args.database
        )
        
        # 获取渠道
        channels = exporter.get_channels(
            include_disabled=args.include_disabled
        )
        
        if not channels:
            log_warning("No channels found in database")
            exporter.close()
            return 1
        
        # 提取API密钥并构建渠道信息
        api_keys_info = exporter.extract_api_keys(channels)
        api_keys = [info['api_key'] for info in api_keys_info]
        
        # 构建渠道信息字典（用于清理功能）
        channel_info = {}
        if args.clean_invalid:
            for channel in channels:
                channel_id = channel.get('id')
                channel_name = channel.get('name', 'Unknown')
                key_str = channel.get('key', '')
                keys = [k.strip() for k in key_str.split('\n') if k.strip() and not k.startswith('[') and not k.startswith('{')]
                
                if keys:
                    channel_info[channel_id] = {
                        'name': channel_name,
                        'keys': keys
                    }
        
        log_info(f"Found {len(api_keys)} API keys from {len(channels)} channels")
        
        # 导出密钥到文件
        if args.export_first or args.export_file:
            export_file = args.export_file or f"exported_keys_{get_timestamp()}.txt"
            exporter.export_to_file(api_keys_info, export_file, format='simple')
        
        exporter.close()
    
    if not api_keys:
        log_warning("No API keys to test")
        return 1
    
    # 批量测试
    results, key_status = batch_test_keys(
        api_keys,
        model=args.model,
        max_workers=args.workers,
        output_file=args.save_results,
        channel_info=channel_info if args.clean_invalid else None
    )
    
    # 清理无效密钥（如果启用）
    if args.clean_invalid and not args.from_file:
        invalid_keys = key_status.get('invalid', [])
        
        if invalid_keys:
            print("\n" + "=" * 60)
            print("INVALID KEYS FOUND")
            print("=" * 60)
            print(f"Found {len(invalid_keys)} invalid API keys")
            
            if not args.no_confirm:
                print("\nThe following operations will be performed:")
                print("1. Remove invalid keys from channels")
                print("2. Disable channels with no valid keys")
                print("\nThis operation CANNOT be undone!")
                
                confirm = input("\nAre you sure you want to clean invalid keys? (yes/N): ")
                if confirm.lower() != 'yes':
                    log_warning("Cleaning cancelled by user")
                    return 0
            
            # 执行清理
            cleaner = DatabaseCleaner(
                host=args.host,
                port=args.port,
                user=args.user,
                password=args.password,
                database=args.database
            )
            
            removed_count = cleaner.remove_invalid_keys(invalid_keys, channel_info)
            cleaner.close()
            
            if removed_count > 0:
                log_success(f"Cleaned {removed_count} invalid keys from database")
            else:
                log_info("No keys were removed")
        else:
            log_info("All tested keys are valid, no cleaning needed")
    
    # 返回状态
    valid_count = sum(1 for r in results if r['success'])
    return 0 if valid_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())