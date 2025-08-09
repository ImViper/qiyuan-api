#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API密钥有效性测试脚本 - 直接数据库版本
直接连接MySQL数据库获取渠道信息
"""

import os
import sys
import json
import time
import argparse
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import (
    log_info, log_success, log_warning, log_error,
    get_timestamp, Colors
)

# 尝试导入MySQL连接库
try:
    import pymysql
    HAS_PYMYSQL = True
except ImportError:
    HAS_PYMYSQL = False
    log_warning("pymysql not installed. Install with: pip install pymysql")

# Gemini API配置
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro", 
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash-8b"
]

# 渠道类型映射
CHANNEL_TYPE_GEMINI = 24
CHANNEL_TYPE_VERTEX = 36

colors = Colors()


class DirectAPIKeyTester:
    """直接数据库API密钥测试器"""
    
    def __init__(self, host: str = "localhost", port: int = 3306,
                 user: str = "root", password: str = "123456",
                 database: str = "new-api"):
        """
        初始化测试器
        
        Args:
            host: MySQL主机
            port: MySQL端口
            user: MySQL用户名
            password: MySQL密码
            database: 数据库名
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.test_results = []
        self.connection = None
        
    def connect_db(self) -> bool:
        """连接数据库"""
        if not HAS_PYMYSQL:
            log_error("pymysql is required. Install with: pip install pymysql")
            return False
            
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            log_success(f"Connected to MySQL database: {self.database}")
            return True
        except Exception as e:
            log_error(f"Failed to connect to database: {e}")
            return False
    
    def get_channels_direct(self, channel_type: Optional[int] = None,
                           status: Optional[int] = None,
                           channel_id: Optional[int] = None) -> List[Dict]:
        """
        直接从数据库获取渠道
        
        Args:
            channel_type: 渠道类型
            status: 渠道状态
            channel_id: 特定渠道ID
        
        Returns:
            渠道列表
        """
        if not self.connection:
            if not self.connect_db():
                return []
        
        try:
            with self.connection.cursor() as cursor:
                # 构建查询
                query = """
                    SELECT id, name, type, `key`, status, base_url, 
                           test_model, models, response_time
                    FROM channels
                    WHERE 1=1
                """
                params = []
                
                if channel_id is not None:
                    query += " AND id = %s"
                    params.append(channel_id)
                elif channel_type is not None:
                    query += " AND type = %s"
                    params.append(channel_type)
                else:
                    # 默认查询Gemini和Vertex类型
                    query += " AND type IN (%s, %s)"
                    params.extend([CHANNEL_TYPE_GEMINI, CHANNEL_TYPE_VERTEX])
                
                if status is not None:
                    query += " AND status = %s"
                    params.append(status)
                
                cursor.execute(query, params)
                channels = cursor.fetchall()
                
                log_info(f"Found {len(channels)} channel(s) in database")
                return channels
                
        except Exception as e:
            log_error(f"Database query failed: {e}")
            return []
    
    def test_gemini_key(self, api_key: str, model: str = "gemini-2.5-flash",
                       base_url: Optional[str] = None, timeout: int = 10) -> Tuple[bool, str, float]:
        """
        测试单个Gemini API密钥
        
        Args:
            api_key: API密钥
            model: 测试模型
            base_url: 自定义base URL
            timeout: 超时时间
        
        Returns:
            (是否成功, 消息, 响应时间)
        """
        if not base_url:
            base_url = GEMINI_BASE_URL
            
        url = f"{base_url}/models/{model}:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": "Say 'test successful' in 3 words only."
                }]
            }],
            "generationConfig": {
                "maxOutputTokens": 10,
                "temperature": 0.1
            }
        }
        
        headers = {"Content-Type": "application/json"}
        start_time = time.time()
        
        try:
            response = requests.post(
                url, json=payload, headers=headers, timeout=timeout
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "candidates" in data and len(data["candidates"]) > 0:
                        return True, "API key is valid", response_time
                    else:
                        return False, "Unexpected response format", response_time
                except json.JSONDecodeError:
                    return False, "Invalid JSON response", response_time
                    
            elif response.status_code == 400:
                return False, "Invalid API key (400)", response_time
            elif response.status_code == 403:
                return False, "API key forbidden (403)", response_time
            elif response.status_code == 404:
                return False, f"Model not found: {model}", response_time
            elif response.status_code == 429:
                return False, "Rate limit exceeded (429)", response_time
            else:
                return False, f"HTTP {response.status_code}", response_time
                
        except requests.exceptions.Timeout:
            return False, f"Timeout ({timeout}s)", timeout * 1000
        except requests.exceptions.ConnectionError:
            return False, "Connection error", 0
        except Exception as e:
            return False, f"Error: {str(e)[:50]}", 0
    
    def test_channel(self, channel: Dict, model: Optional[str] = None) -> Dict:
        """测试单个渠道"""
        channel_id = channel.get('id', 0)
        channel_name = channel.get('name', 'Unknown')
        api_key = channel.get('key', '')
        base_url = channel.get('base_url', '')
        test_model = channel.get('test_model', '')
        
        # 确定测试模型
        if not model:
            if test_model:
                model = test_model
            else:
                models_str = channel.get('models', '')
                if models_str:
                    models = [m.strip() for m in models_str.split(',')]
                    for m in models:
                        if 'gemini' in m.lower():
                            model = m
                            break
                    if not model and models:
                        model = models[0]
                
                if not model:
                    model = "gemini-2.5-flash"
        
        # 处理多个API密钥
        api_keys = [k.strip() for k in api_key.split('\n') if k.strip()]
        
        if not api_keys:
            return {
                'channel_id': channel_id,
                'channel_name': channel_name,
                'success': False,
                'message': 'No API key found',
                'model': model,
                'response_time': 0
            }
        
        # 测试第一个有效的密钥
        for idx, key in enumerate(api_keys):
            if key.startswith('[') or key.startswith('{'):
                continue
                
            success, message, response_time = self.test_gemini_key(
                key, model, base_url if base_url else None
            )
            
            if success or idx == len(api_keys) - 1:
                return {
                    'channel_id': channel_id,
                    'channel_name': channel_name,
                    'success': success,
                    'message': message,
                    'model': model,
                    'response_time': response_time,
                    'key_index': idx if len(api_keys) > 1 else -1,
                    'total_keys': len(api_keys)
                }
        
        return {
            'channel_id': channel_id,
            'channel_name': channel_name,
            'success': False,
            'message': 'No valid API key',
            'model': model,
            'response_time': 0
        }
    
    def test_channels_batch(self, channels: List[Dict], model: Optional[str] = None,
                           max_workers: int = 5) -> List[Dict]:
        """批量测试渠道"""
        results = []
        total = len(channels)
        
        if total == 0:
            log_warning("No channels to test")
            return results
        
        log_info(f"Testing {total} channels with {max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_channel = {
                executor.submit(self.test_channel, channel, model): channel
                for channel in channels
            }
            
            completed = 0
            for future in as_completed(future_to_channel):
                channel = future_to_channel[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1
                    
                    status_icon = "[OK]" if result['success'] else "[FAIL]"
                    print(f"[{completed}/{total}] {status_icon} {result['channel_name']}: "
                          f"{result['message']} ({result['response_time']:.0f}ms)")
                    
                except Exception as e:
                    completed += 1
                    log_error(f"Error testing channel: {e}")
                    results.append({
                        'channel_id': channel.get('id', 0),
                        'channel_name': channel.get('name', 'Unknown'),
                        'success': False,
                        'message': f"Test error: {str(e)}",
                        'response_time': 0
                    })
        
        return results
    
    def print_summary(self, results: List[Dict]):
        """打印测试摘要"""
        if not results:
            log_warning("No test results")
            return
        
        total = len(results)
        successful = sum(1 for r in results if r['success'])
        failed = total - successful
        
        print("\n" + "=" * 60)
        print("测试结果摘要")
        print("=" * 60)
        
        print(f"\n总计: {total} 个渠道")
        print(f"{colors.GREEN}成功: {successful}{colors.NC}")
        print(f"{colors.RED}失败: {failed}{colors.NC}")
        
        if total > 0:
            print(f"成功率: {successful/total*100:.1f}%")
        
        # 平均响应时间
        success_times = [r['response_time'] for r in results if r['success']]
        if success_times:
            avg_time = sum(success_times) / len(success_times)
            print(f"平均响应时间: {avg_time:.0f}ms")
        
        # 显示失败的渠道
        if failed > 0:
            print(f"\n{colors.RED}失败的渠道:{colors.NC}")
            for r in results:
                if not r['success']:
                    print(f"  - [{r['channel_id']}] {r['channel_name']}: {r['message']}")
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='API密钥测试工具 - 直接数据库版本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                              # 测试所有Gemini渠道
  %(prog)s --model gemini-2.5-flash    # 指定测试模型
  %(prog)s --status 1                   # 仅测试启用的渠道
  %(prog)s --channel-id 5              # 测试特定渠道
  %(prog)s --api-key "YOUR_KEY"        # 直接测试API密钥
  
数据库连接:
  %(prog)s --host localhost --port 3306 --user root --password 123456
        """
    )
    
    # 数据库连接参数
    parser.add_argument('--host', default='localhost',
                       help='MySQL主机 (默认: localhost)')
    parser.add_argument('--port', type=int, default=3306,
                       help='MySQL端口 (默认: 3306)')
    parser.add_argument('--user', default='root',
                       help='MySQL用户名 (默认: root)')
    parser.add_argument('--password', default='123456',
                       help='MySQL密码 (默认: 123456)')
    parser.add_argument('--database', default='new-api',
                       help='数据库名 (默认: new-api)')
    
    # 测试参数
    parser.add_argument('--model',
                       help='指定测试模型')
    parser.add_argument('--status', type=int,
                       help='渠道状态 (1=启用, 2=禁用, 3=自动禁用)')
    parser.add_argument('--channel-id', type=int,
                       help='测试特定渠道ID')
    parser.add_argument('--api-key',
                       help='直接测试API密钥')
    parser.add_argument('--workers', type=int, default=5,
                       help='并发数 (默认: 5)')
    parser.add_argument('--list-models', action='store_true',
                       help='列出支持的模型')
    
    args = parser.parse_args()
    
    # 列出支持的模型
    if args.list_models:
        print("支持的Gemini模型:")
        for model in GEMINI_MODELS:
            print(f"  - {model}")
        return 0
    
    # 创建测试器
    tester = DirectAPIKeyTester(
        host=args.host,
        port=args.port,
        user=args.user,
        password=args.password,
        database=args.database
    )
    
    # 直接测试API密钥
    if args.api_key:
        model = args.model or "gemini-2.5-flash"
        log_info(f"Testing API key with model: {model}")
        
        success, message, response_time = tester.test_gemini_key(args.api_key, model)
        
        if success:
            log_success(f"Valid! Response: {response_time:.0f}ms")
        else:
            log_error(f"Failed: {message}")
        
        return 0 if success else 1
    
    # 从数据库获取渠道
    if not HAS_PYMYSQL:
        print("\n" + "=" * 60)
        print("需要安装pymysql库来连接数据库")
        print("=" * 60)
        print("\n安装方法:")
        print("  pip install pymysql")
        print("\n或者使用conda:")
        print("  conda install pymysql")
        return 1
    
    channels = tester.get_channels_direct(
        channel_id=args.channel_id,
        status=args.status
    )
    
    if not channels:
        log_warning("No channels found")
        tester.close()
        return 1
    
    # 批量测试
    results = tester.test_channels_batch(
        channels,
        model=args.model,
        max_workers=args.workers
    )
    
    # 打印摘要
    tester.print_summary(results)
    
    # 关闭连接
    tester.close()
    
    # 返回状态
    failed_count = sum(1 for r in results if not r['success'])
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())