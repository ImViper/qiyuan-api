#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的Gemini API密钥测试脚本
直接测试API密钥，不依赖数据库
"""

import sys
import json
import time
import argparse
import requests

def test_gemini_key(api_key, model="gemini-2.5-flash"):
    """
    测试Gemini API密钥
    
    Args:
        api_key: API密钥
        model: 模型名称
    
    Returns:
        (成功, 消息, 响应时间毫秒)
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    
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
    
    print(f"Testing API key with model: {model}")
    print(f"URL: {url[:50]}...")
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response_time = (time.time() - start_time) * 1000
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                content = data["candidates"][0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text = parts[0].get("text", "")
                    print(f"Response: {text}")
                return True, "API key is valid", response_time
            else:
                return False, "Unexpected response format", response_time
                
        elif response.status_code == 400:
            return False, "Invalid API key (400 Bad Request)", response_time
            
        elif response.status_code == 403:
            error_msg = "API key forbidden (403)"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg = f"403: {error_data['error'].get('message', 'Forbidden')}"
            except:
                pass
            return False, error_msg, response_time
            
        elif response.status_code == 404:
            return False, f"Model not found: {model}", response_time
            
        elif response.status_code == 429:
            return False, "Rate limit exceeded (429)", response_time
            
        else:
            error_text = response.text[:200] if response.text else ""
            return False, f"HTTP {response.status_code}: {error_text}", response_time
            
    except requests.exceptions.Timeout:
        return False, "Request timeout (10s)", 10000
        
    except requests.exceptions.ConnectionError as e:
        return False, f"Connection error: {str(e)[:100]}", 0
        
    except Exception as e:
        return False, f"Error: {str(e)[:100]}", 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Simple Gemini API Key Tester',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s YOUR_API_KEY
  %(prog)s YOUR_API_KEY --model gemini-2.5-pro
  %(prog)s --list-models
        """
    )
    
    parser.add_argument('api_key', nargs='?',
                       help='Gemini API key to test')
    
    parser.add_argument('--model', default='gemini-2.5-flash',
                       help='Model to test (default: gemini-2.5-flash)')
    
    parser.add_argument('--list-models', action='store_true',
                       help='List supported models')
    
    args = parser.parse_args()
    
    # 列出支持的模型
    if args.list_models:
        print("Supported Gemini models:")
        models = [
            "gemini-2.5-flash (recommended)",
            "gemini-2.5-pro",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash-8b"
        ]
        for model in models:
            print(f"  - {model}")
        return 0
    
    # 检查API密钥
    if not args.api_key:
        print("Error: Please provide an API key")
        print("Usage: python test_gemini_simple.py YOUR_API_KEY")
        return 1
    
    # 测试API密钥
    print("=" * 60)
    print("Gemini API Key Test")
    print("=" * 60)
    
    success, message, response_time = test_gemini_key(args.api_key, args.model)
    
    print("\n" + "=" * 60)
    print("Test Result")
    print("=" * 60)
    
    if success:
        print(f"Status: SUCCESS")
        print(f"Message: {message}")
        print(f"Response Time: {response_time:.0f}ms")
        print("\nYour Gemini API key is working correctly!")
        return 0
    else:
        print(f"Status: FAILED")
        print(f"Message: {message}")
        print(f"Response Time: {response_time:.0f}ms")
        print("\nYour API key test failed. Please check:")
        print("1. The API key is correct and active")
        print("2. The API key has not exceeded quota limits")
        print("3. The model name is correct")
        print("4. Your network can access Google APIs")
        return 1


if __name__ == "__main__":
    sys.exit(main())