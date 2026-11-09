#!/usr/bin/env python3
"""测试腾讯K线的正确参数格式"""
import requests
import json
import time

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

# 根据 vibe 源码，腾讯K线接口的正确格式
# URL模式: http://web.ifzq.gtimg.cn/appstock/app/fqkline/get
# 参数: _var, param=<code>,<period>,,<count>

test_cases = [
    ("sz300308", "day", 10),
    ("sz300308", "week", 10),
    ("sz300308", "month", 10),
]

for code, period, count in test_cases:
    print(f"\n=== 测试: {code} - {period} ===")
    
    url = "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
    params = {
        "_var": f"{period}_qfq",
        "param": f"{code},{period},,{count}",
        "r": str(int(time.time() * 1000))
    }
    
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        print(f"Status: {resp.status_code}")
        print(f"Response length: {len(resp.text)}")
        print(f"Response (first 300 chars): {resp.text[:300]}")
        
        # 尝试解析
        text = resp.text
        if "=" in text and "{" in text:
            json_part = text.split("=", 1)[1].strip()
            # 去掉可能的尾部分号
            if json_part.endswith(";"):
                json_part = json_part[:-1]
            
            data = json.loads(json_part)
            print(f"解析成功!")
            print(f"  code: {data.get('code')}")
            print(f"  msg: {data.get('msg')}")
            
            # 检查数据
            if code in data.get("data", {}):
                stock_data = data["data"][code]
                print(f"  返回的keys: {list(stock_data.keys())}")
                
                # 查找K线数据
                for key in stock_data.keys():
                    if isinstance(stock_data[key], list):
                        print(f"  {key}: {len(stock_data[key])} 条")
                        if stock_data[key]:
                            print(f"    样例: {stock_data[key][0]}")
        
    except Exception as e:
        print(f"错误: {str(e)}")
    
    time.sleep(1)
