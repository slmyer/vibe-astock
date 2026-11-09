#!/usr/bin/env python3
"""快速诊断各个接口的实际响应"""
import requests
import time

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0'})

print("=== 1. 上交所ETF份额 (515050) ===")
url1 = "https://query.sse.com.cn/commonQuery.do"
params1 = {"isPagination": "false", "sqlId": "COMMON_SSE_ZQPZ_ETFLB_L", "fundid": "515050"}
resp1 = session.get(url1, params=params1, timeout=10)
print(f"Status: {resp1.status_code}")
print(f"Content-Type: {resp1.headers.get('Content-Type')}")
print(f"Content (first 500 chars):\n{resp1.text[:500]}\n")
time.sleep(1)

print("=== 2. 东财主力资金流 lmt=120 (300308) ===")
url2 = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
params2 = {
    "lmt": 120, "klt": "101", "secid": "0.300308",
    "fields1": "f1,f2,f3,f7",
    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
    "ut": "fa5fd1943c7b386f172d6893dbfba10b"
}
resp2 = session.get(url2, params=params2, timeout=10)
print(f"Status: {resp2.status_code}")
data2 = resp2.json()
klines = data2.get("data", {}).get("klines", [])
print(f"返回条数: {len(klines)}")
if klines:
    print(f"最早日期: {klines[-1].split(',')[0]}")
    print(f"最晚日期: {klines[0].split(',')[0]}")
print()
time.sleep(1)

print("=== 3. 东财主力资金流 lmt=500 (300308) ===")
params3 = params2.copy()
params3["lmt"] = 500
resp3 = session.get(url2, params=params3, timeout=10)
data3 = resp3.json()
klines3 = data3.get("data", {}).get("klines", [])
print(f"返回条数: {len(klines3)}")
if klines3:
    print(f"最早日期: {klines3[-1].split(',')[0]}")
    print(f"最晚日期: {klines3[0].split(',')[0]}")
print()
time.sleep(1)

print("=== 4. 中证指数权重 (000300) ===")
url4 = "https://www.csindex.com.cn/uploads/file/autofile/closeweight/000300closeweight.xls"
resp4 = session.get(url4, timeout=15)
print(f"Status: {resp4.status_code}")
print(f"Content-Type: {resp4.headers.get('Content-Type')}")
print(f"Content-Length: {len(resp4.content)}")
print(f"Content (first 500 chars):\n{resp4.text[:500]}\n")
time.sleep(1)

print("=== 5. 腾讯K线 day (sz300308) ===")
url5 = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
params5 = {"_var": "dayfq", "param": "sz300308,day,,10", "r": str(int(time.time()))}
resp5 = session.get(url5, params=params5, timeout=10)
print(f"Status: {resp5.status_code}")
print(f"Response: {resp5.text[:300]}")
