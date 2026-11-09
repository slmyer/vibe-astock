# 数据可行性验证测试 (2026-11-09)

本目录包含对 vibe-astock 数据适配层与 TradingAgents-astock 资金接口的最小化实测。

## 背景

验证用户提出的 5 项数据能力：
1. ETF 515050/560780 上交所历史份额
2. 东财主力资金 lmt120 vs 500 对比
3. 中证/国证权重快照和历史 as-of 能力
4. 新浪资金与东财定义差异
5. 腾讯日/周/月 OHLCV 复权语义

## 测试约束

- ✅ 独立云环境 (Cloud VM)
- ✅ 不付费、不用私人凭证
- ✅ 低请求量 (~3次/接口)，原限速 (≥1s)
- ⚠️ **结果不代表用户本地电脑可用**

## 核心发现

### ✓ 东财主力资金流 (部分通过但受限)

- **lmt=120**: 返回 120 条，最早 2026-05-15 (~6 个月)
- **lmt=500**: 返回 121 条，最早 2026-05-14 (仅多 1 天)
- ⚠️ **lmt 参数未显著扩大时间窗口**

### ✗ 上交所 ETF 份额 (失败)

- 接口返回: `System Error, Please try again later...`
- 可能需特殊 headers 或已失效

### ✗ 中证指数权重 (失败)

- 返回 HTML 页面而非 Excel 文件
- URL 可能已失效

### ✗ 腾讯 K 线 (失败)

- 返回 `param error`
- 接口参数可能已变更

## 文件说明

| 文件 | 用途 |
|------|------|
| `FINDINGS_CN.md` | 完整中文结论报告 |
| `evidence_normalized.csv` | 规范化证据表 (10 项测试) |
| `test_summary.json` | 完整JSON证据 (含原始响应) |
| `requirements_minimal.txt` | 最小依赖 |
| `diagnose.py` | **独立诊断脚本 (可脱离仓库运行)** |
| `smoke_test.py` | 完整测试框架 |
| `*.log` | 测试运行日志 |

## 复跑方法

### 最小诊断 (推荐用户本地复测)

```bash
# 无需 clone 仓库，仅需 requests
pip install requests
python diagnose.py
```

### 完整测试

```bash
pip install -r requirements_minimal.txt
python smoke_test.py
```

## 下一步

1. **用户本地复测**: 使用 `diagnose.py` 在原电脑验证东财接口
2. **排查失败项**: 
   - 上交所: 检查 vibe 源码中的 headers
   - 中证权重: 手动访问官网找实际下载路径
   - 腾讯K线: 复查 vibe 源码中的参数格式
3. **评估替代方案**: 
   - ETF份额: 用户已有东财 RPT_ETF_SCALE
   - 权重: 评估「最近快照」vs「历史 as-of」需求

---

**测试时间**: 2026-11-09 08:15-08:18 UTC  
**执行环境**: Cloud Agent VM  
**分支**: cursor/data-feasibility-smoke-48aa
