#!/usr/bin/env python3
"""
数据可行性独立验证脚本
可脱离 vibe-astock 和 TradingAgents 仓库运行
"""
import json
import time
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import sys

try:
    import requests
    import pandas as pd
except ImportError as e:
    print(f"缺少依赖: {e}")
    print("请先运行: pip install requests pandas lxml openpyxl")
    sys.exit(1)


class TestResult:
    """测试结果记录器"""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.status = "未验证"  # 通过/失败/未验证
        self.error_category = None  # 依赖/网络/鉴权/字段/口径/历史as-of/许可未知
        self.timestamp = datetime.datetime.now().isoformat()
        self.request_params = {}
        self.response_data = {}
        self.evidence = {}
        self.notes = []
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "status": self.status,
            "error_category": self.error_category,
            "timestamp": self.timestamp,
            "request_params": self.request_params,
            "response_data": self.response_data,
            "evidence": self.evidence,
            "notes": self.notes
        }


class MinimalHTTPClient:
    """最小化HTTP客户端 - 带限速和重试"""
    
    def __init__(self, min_interval: float = 1.0, max_retries: int = 3):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.min_interval = min_interval
        self.max_retries = max_retries
        self.last_request_time = 0
        
    def get(self, url: str, params: Optional[Dict] = None, timeout: int = 10) -> requests.Response:
        """带限速的GET请求"""
        # 限速
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
            
        # 重试
        for attempt in range(self.max_retries):
            try:
                self.last_request_time = time.time()
                resp = self.session.get(url, params=params, timeout=timeout)
                return resp
            except (requests.RequestException, Exception) as e:
                if attempt == self.max_retries - 1:
                    raise
                wait_time = 2 ** attempt  # 指数退避
                time.sleep(wait_time)
        
        raise Exception("不应到达此处")


class DataFeasibilityTester:
    """数据可行性测试器"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.results: List[TestResult] = []
        self.http = MinimalHTTPClient()
        
    def save_results(self):
        """保存所有测试结果"""
        summary_file = self.output_dir / "test_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump([r.to_dict() for r in self.results], f, ensure_ascii=False, indent=2)
        print(f"\n测试结果已保存到: {summary_file}")
        
    def test_sse_etf_shares(self, etf_codes: List[str], test_date: str = "2024-09-24"):
        """测试1: 上交所ETF份额历史数据"""
        print("\n=== 测试1: 上交所ETF份额历史数据 ===")
        
        for code in etf_codes:
            result = TestResult(f"SSE_ETF_Shares_{code}")
            result.request_params = {
                "etf_code": code,
                "test_date": test_date,
                "source": "上交所"
            }
            
            try:
                # 上交所ETF每日申赎清单归档
                # 根据vibe源码: https://query.sse.com.cn/commonQuery.do?isPagination=false
                url = "https://query.sse.com.cn/commonQuery.do"
                params = {
                    "isPagination": "false",
                    "sqlId": "COMMON_SSE_ZQPZ_ETFLB_L",
                    "fundid": code
                }
                
                result.notes.append(f"请求 {url} with fundid={code}")
                resp = self.http.get(url, params=params)
                
                result.response_data = {
                    "status_code": resp.status_code,
                    "headers": dict(resp.headers),
                    "content_length": len(resp.content)
                }
                
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                    except Exception as json_err:
                        # 可能返回了HTML错误页或需要特殊headers
                        result.status = "失败"
                        result.error_category = "鉴权/付费"
                        result.notes.append(f"JSON解析失败: {str(json_err)}")
                        result.evidence["response_text_sample"] = resp.text[:500]
                        self.results.append(result)
                        continue
                        
                    result.evidence["response_sample"] = data
                    
                    # 检查数据
                    if "result" in data:
                        rows = data.get("result", [])
                        result.evidence["row_count"] = len(rows)
                        
                        if rows:
                            df = pd.DataFrame(rows)
                            result.evidence["columns"] = list(df.columns)
                            
                            # 检查日期范围
                            if "TRADE_DATE" in df.columns or "trade_date" in df.columns:
                                date_col = "TRADE_DATE" if "TRADE_DATE" in df.columns else "trade_date"
                                result.evidence["date_range"] = {
                                    "min": str(df[date_col].min()),
                                    "max": str(df[date_col].max())
                                }
                                
                                # 检查2024-09-24以来覆盖
                                target_date = pd.to_datetime(test_date)
                                df[date_col] = pd.to_datetime(df[date_col])
                                recent = df[df[date_col] >= target_date]
                                result.evidence["coverage_since_20240924"] = len(recent)
                                
                            # 检查份额字段
                            share_cols = [c for c in df.columns if 'share' in c.lower() or '份额' in c or '基金' in c]
                            result.evidence["share_columns"] = share_cols
                            
                            result.status = "通过"
                            result.notes.append(f"成功获取 {len(rows)} 行数据")
                        else:
                            result.status = "失败"
                            result.error_category = "字段/日期覆盖"
                            result.notes.append("返回数据为空")
                    else:
                        result.status = "失败"
                        result.error_category = "字段/日期覆盖"
                        result.notes.append(f"响应格式异常: {list(data.keys())}")
                else:
                    result.status = "失败"
                    result.error_category = "网络/DNS/TLS/HTTP"
                    result.notes.append(f"HTTP {resp.status_code}")
                    
            except requests.RequestException as e:
                result.status = "失败"
                result.error_category = "网络/DNS/TLS/HTTP"
                result.notes.append(f"网络错误: {str(e)}")
            except Exception as e:
                result.status = "失败"
                result.error_category = "依赖"
                result.notes.append(f"未知错误: {str(e)}")
                
            self.results.append(result)
            print(f"  {code}: {result.status} - {result.notes[-1] if result.notes else ''}")
            
    def test_eastmoney_fund_flow(self, secid: str, symbol: str):
        """测试2: 东财主力资金流 - lmt 120 vs 500 对比"""
        print(f"\n=== 测试2: 东财主力资金流对比 ({symbol}) ===")
        
        for lmt in [120, 500]:
            result = TestResult(f"EM_FundFlow_lmt{lmt}_{symbol}")
            result.request_params = {
                "secid": secid,
                "symbol": symbol,
                "lmt": lmt,
                "source": "东财push2his"
            }
            
            try:
                # 东财历史主力资金流接口
                # 参考 TradingAgents: push2his.eastmoney.com/api/qt/stock/fflow/daykline/get
                url = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
                params = {
                    "lmt": lmt,
                    "klt": "101",  # 日线
                    "secid": secid,
                    "fields1": "f1,f2,f3,f7",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
                    "ut": "fa5fd1943c7b386f172d6893dbfba10b"
                }
                
                result.notes.append(f"请求 lmt={lmt}")
                resp = self.http.get(url, params=params, timeout=15)
                
                result.response_data = {
                    "status_code": resp.status_code,
                    "content_length": len(resp.content)
                }
                
                if resp.status_code == 200:
                    data = resp.json()
                    result.evidence["response_sample"] = data
                    
                    # 解析返回数据
                    if "data" in data and data["data"]:
                        klines = data["data"].get("klines", [])
                        result.evidence["actual_rows"] = len(klines)
                        
                        if klines:
                            # 解析日期范围
                            dates = [k.split(",")[0] for k in klines]
                            result.evidence["date_range"] = {
                                "min": dates[-1] if dates else None,  # 最早
                                "max": dates[0] if dates else None    # 最晚
                            }
                            
                            result.status = "通过"
                            result.notes.append(f"返回 {len(klines)} 条记录")
                        else:
                            result.status = "失败"
                            result.error_category = "字段/日期覆盖"
                            result.notes.append("klines 为空")
                    else:
                        result.status = "失败"
                        result.error_category = "字段/日期覆盖"
                        result.notes.append("data 字段为空或不存在")
                else:
                    result.status = "失败"
                    result.error_category = "网络/DNS/TLS/HTTP"
                    result.notes.append(f"HTTP {resp.status_code}")
                    
            except requests.RequestException as e:
                result.status = "失败"
                result.error_category = "网络/DNS/TLS/HTTP"
                result.notes.append(f"网络错误: {str(e)}")
            except Exception as e:
                result.status = "失败"
                result.error_category = "依赖"
                result.notes.append(f"错误: {str(e)}")
                
            self.results.append(result)
            print(f"  lmt={lmt}: {result.status} - {result.notes[-1] if result.notes else ''}")
            
    def test_csi_index_weights(self, index_code: str = "000300"):
        """测试3: 中证指数权重快照"""
        print(f"\n=== 测试3: 中证指数权重快照 ({index_code}) ===")
        
        result = TestResult(f"CSI_Weights_{index_code}")
        result.request_params = {
            "index_code": index_code,
            "source": "中证指数"
        }
        
        try:
            # 中证指数权重文件 - 根据vibe源码
            url = f"https://www.csindex.com.cn/uploads/file/autofile/closeweight/{index_code}closeweight.xls"
            
            result.notes.append(f"请求权重文件: {url}")
            resp = self.http.get(url, timeout=15)
            
            result.response_data = {
                "status_code": resp.status_code,
                "content_type": resp.headers.get("Content-Type", ""),
                "content_length": len(resp.content)
            }
            
            if resp.status_code == 200:
                # 尝试解析Excel
                try:
                    from io import BytesIO
                    df = pd.read_excel(BytesIO(resp.content))
                    result.evidence["row_count"] = len(df)
                    result.evidence["columns"] = list(df.columns)
                    result.evidence["sample_head"] = df.head(3).to_dict()
                    
                    # 检查日期字段
                    date_cols = [c for c in df.columns if 'date' in str(c).lower() or '日期' in str(c)]
                    result.evidence["date_columns"] = date_cols
                    
                    if date_cols:
                        # 检查日期唯一性 (vibe要求date.nunique()==1)
                        for dcol in date_cols:
                            unique_dates = df[dcol].nunique()
                            result.evidence[f"{dcol}_unique_count"] = unique_dates
                            result.evidence[f"{dcol}_values"] = df[dcol].unique().tolist()[:5]
                    
                    # 标注: 这是最近公布的快照，无as-of参数
                    result.notes.append("注意: 无历史as-of参数，这是当前最新快照")
                    result.notes.append("文件日期 ≠ 首次可知日期，不可倒填历史回测")
                    
                    result.status = "通过"
                    result.notes.append(f"成功解析权重文件: {len(df)} 成分")
                    
                except Exception as e:
                    result.status = "失败"
                    result.error_category = "字段/日期覆盖"
                    result.notes.append(f"Excel解析失败: {str(e)}")
            else:
                result.status = "失败"
                result.error_category = "网络/DNS/TLS/HTTP"
                result.notes.append(f"HTTP {resp.status_code}")
                
        except requests.RequestException as e:
            result.status = "失败"
            result.error_category = "网络/DNS/TLS/HTTP"
            result.notes.append(f"网络错误: {str(e)}")
        except Exception as e:
            result.status = "失败"
            result.error_category = "依赖"
            result.notes.append(f"错误: {str(e)}")
            
        self.results.append(result)
        print(f"  {result.status} - {result.notes[-1] if result.notes else ''}")
        
    def test_tencent_kline(self, symbol: str, periods: List[str]):
        """测试5: 腾讯K线复权语义"""
        print(f"\n=== 测试5: 腾讯K线复权语义 ({symbol}) ===")
        
        for period in periods:
            result = TestResult(f"Tencent_Kline_{period}_{symbol}")
            result.request_params = {
                "symbol": symbol,
                "period": period,
                "source": "腾讯"
            }
            
            try:
                # 腾讯K线接口 - fqkline
                # 根据vibe源码: qt.gtimg.cn/q=<period>fq<symbol>
                # period: day/week/month
                url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
                params = {
                    "_var": f"{period}fq",
                    "param": f"{symbol},{period},,10",  # 最后参数是条数
                    "r": str(int(time.time()))
                }
                
                result.notes.append(f"测试 period={period}")
                resp = self.http.get(url, params=params)
                
                result.response_data = {
                    "status_code": resp.status_code,
                    "content_length": len(resp.content)
                }
                
                if resp.status_code == 200:
                    # 腾讯返回的是JSONP，需要提取JSON部分
                    text = resp.text
                    result.evidence["raw_response_sample"] = text[:200]
                    
                    # 处理多种可能的JSONP格式
                    if "={" in text:
                        json_str = "{" + text.split("={", 1)[1]
                        # 移除可能的尾部分号或其他字符
                        json_str = json_str.rsplit("}", 1)[0] + "}"
                    elif text.startswith("{"):
                        json_str = text
                    else:
                        result.status = "失败"
                        result.error_category = "字段/日期覆盖"
                        result.notes.append(f"无法识别的响应格式")
                        self.results.append(result)
                        continue
                    
                    try:
                        data = json.loads(json_str)
                    except json.JSONDecodeError as e:
                        result.status = "失败"
                        result.error_category = "字段/日期覆盖"
                        result.notes.append(f"JSON解析错误: {str(e)}")
                        self.results.append(result)
                        continue
                        
                        result.evidence["response_sample"] = data
                        
                        # 检查数据结构
                        if "data" in data:
                            symbol_data = data["data"].get(symbol, {})
                            if f"qfq{period}" in symbol_data or period in symbol_data:
                                kline_key = f"qfq{period}" if f"qfq{period}" in symbol_data else period
                                klines = symbol_data.get(kline_key, [])
                                
                                result.evidence["actual_rows"] = len(klines)
                                result.evidence["kline_key"] = kline_key
                                
                                if klines:
                                    result.evidence["sample_data"] = klines[:2]
                                    result.status = "通过"
                                    result.notes.append(f"获取到 {len(klines)} 条K线")
                                    result.notes.append("默认为前复权(qfq)")
                                else:
                                    result.status = "失败"
                                    result.error_category = "字段/日期覆盖"
                                    result.notes.append("K线数据为空")
                            else:
                                result.status = "失败"
                                result.error_category = "字段/日期覆盖"
                                result.notes.append(f"未找到K线数据key: {list(symbol_data.keys())}")
                        else:
                            result.status = "失败"
                            result.error_category = "字段/日期覆盖"
                            result.notes.append("响应无data字段")
                    else:
                        result.status = "失败"
                        result.error_category = "字段/日期覆盖"
                        result.notes.append("JSONP格式异常")
                else:
                    result.status = "失败"
                    result.error_category = "网络/DNS/TLS/HTTP"
                    result.notes.append(f"HTTP {resp.status_code}")
                    
            except requests.RequestException as e:
                result.status = "失败"
                result.error_category = "网络/DNS/TLS/HTTP"
                result.notes.append(f"网络错误: {str(e)}")
            except Exception as e:
                result.status = "失败"
                result.error_category = "依赖"
                result.notes.append(f"错误: {str(e)}")
                
            self.results.append(result)
            print(f"  {period}: {result.status} - {result.notes[-1] if result.notes else ''}")
            

def main():
    """主测试流程"""
    print("=" * 60)
    print("数据可行性独立验证 - Smoke Test")
    print("环境: 独立云环境 (不代表用户本地可用)")
    print("=" * 60)
    
    output_dir = Path("/tmp/data_feasibility_test/results")
    tester = DataFeasibilityTester(output_dir)
    
    try:
        # 测试1: ETF份额
        tester.test_sse_etf_shares(
            etf_codes=["515050", "560780"],
            test_date="2024-09-24"
        )
        
        # 测试2: 东财主力资金流 (lmt对比)
        # 300308 是用户指定的样本
        tester.test_eastmoney_fund_flow(
            secid="0.300308",
            symbol="中际旭创"
        )
        
        # 也测试一个ETF
        tester.test_eastmoney_fund_flow(
            secid="1.515050",
            symbol="科创50ETF"
        )
        
        # 测试3: 中证指数权重
        tester.test_csi_index_weights(index_code="000300")  # 沪深300
        
        # 测试5: 腾讯K线复权
        tester.test_tencent_kline(
            symbol="sz300308",  # 中际旭创
            periods=["day", "week", "month"]
        )
        
        # 保存结果
        tester.save_results()
        
        # 打印汇总
        print("\n" + "=" * 60)
        print("测试汇总:")
        passed = sum(1 for r in tester.results if r.status == "通过")
        failed = sum(1 for r in tester.results if r.status == "失败")
        print(f"  通过: {passed}")
        print(f"  失败: {failed}")
        print(f"  未验证: {len(tester.results) - passed - failed}")
        print("=" * 60)
        
        return 0 if failed == 0 else 1
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        return 130
    except Exception as e:
        print(f"\n\n测试框架错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
