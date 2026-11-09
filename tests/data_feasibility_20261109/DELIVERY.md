# 数据可行性验证 - 交付清单

**任务完成时间**: 2026-11-09 08:30 UTC  
**执行者**: Cursor Cloud Agent  
**PR**: https://github.com/slmyer/vibe-astock/pull/1

---

## 一、简短结论（中文）

### 核心发现

1. **东财主力资金流** ✓ (有限制)
   - 云端能连通，lmt=120 和 500 均成功
   - **关键**: lmt=500 仅返回 121 条 (vs 120 条)，最早 2026-05-14
   - **未证明能突破 ~6 个月窗口**，与用户现有 121 日基本一致
   - 不阻塞短期验证，但**长窗口训练数据存疑**

2. **上交所 ETF 份额** ✗ (阻塞)
   - 接口返回 `System Error`
   - 可能需特殊 headers 或已失效
   - 建议: 检查 vibe 源码或改用东财 RPT_ETF_SCALE

3. **中证指数权重** ✗ (阻塞)
   - 返回 HTML 页面而非 Excel
   - URL 已失效或改版
   - 建议: 手动访问官网找新路径

4. **腾讯 K 线** ✗ (阻塞)
   - 返回 `param error`
   - 接口可能已变更
   - 建议: 复查 vibe 源码实际参数

5. **新浪资金** (未测)
   - 时间限制未完成
   - 建议后续补测

### 重要警告

⚠️ **本次测试在独立云环境进行，结果不代表用户本地电脑可用**

- 云端 IP/DNS/出口与用户环境不同
- 东财成功 ≠ box 可用
- **必须用户本地复测**

---

## 二、Artifacts 路径

所有文件位于: `/workspace/tests/data_feasibility_20261109/`

### 核心交付物

| 文件 | 说明 |
|------|------|
| `FINDINGS_CN.md` | **完整中文结论报告** (含详细分析) |
| `evidence_normalized.csv` | **规范化证据表** (10 项测试，含日期/条数) |
| `test_summary.json` | 完整JSON证据 (含原始响应) |
| `README.md` | 本次测试说明 |
| `DELIVERY.md` | 本交付清单 |

### 可复跑脚本 (独立运行，无需仓库)

| 脚本 | 用途 |
|------|------|
| `diagnose.py` | **快速诊断** (5 个接口) — **推荐用户本地复测** |
| `smoke_test.py` | 完整测试框架 (含限速/重试/证据保存) |
| `test_tencent_kline.py` | 腾讯K线参数调试 |
| `requirements_minimal.txt` | 最小依赖 (requests, pandas, lxml, openpyxl) |

### 原始日志

- `smoke_test.log` / `smoke_test_v2.log`: 测试运行日志

---

## 三、复跑命令

### 方案1: 最小诊断 (推荐用户本地)

```bash
# 仅需 requests，无需 clone 仓库
pip install requests

# 5 个接口快速检查 (10 秒完成)
python diagnose.py
```

**输出**: 每个接口的 HTTP 状态、返回条数、日期范围

### 方案2: 完整测试

```bash
# 安装依赖
pip install -r requirements_minimal.txt

# 运行完整测试 (含限速、重试、证据保存)
python smoke_test.py

# 查看结果
cat results/FINDINGS_CN.md
```

**输出**: 
- `results/test_summary.json`: 完整JSON证据
- `results/evidence_normalized.csv`: 规范化表格
- `results/FINDINGS_CN.md`: 中文报告

### 方案3: 单独测试腾讯K线

```bash
python test_tencent_kline.py
```

---

## 四、证据 Schema

`evidence_normalized.csv` 列定义:

| 列名 | 示例 |
|------|------|
| `test_id` | 1, 2, 3... |
| `data_source` | eastmoney_fund_flow, sse_etf_shares |
| `api_endpoint` | push2his.eastmoney.com/... |
| `secid_or_symbol` | 0.300308 (中际旭创) |
| `request_param_lmt` | 120, 500 |
| `test_env` | cloud_vm |
| `status` | 通过 / 失败 |
| `http_status_code` | 200, 404... |
| `actual_rows_returned` | 120, 121 |
| `date_range_min` | 2026-05-14 |
| `date_range_max` | 2026-11-09 |
| `error_category` | 网络/DNS/TLS/HTTP, 字段/日期覆盖, 鉴权/付费, 依赖, 历史as-of, 许可未知 |
| `key_finding` | lmt=500仅返回121条仍约6个月 |
| `notes` | 补充说明 |

---

## 五、阻塞清单与下一步

### 当前阻塞

1. ❌ **上交所 ETF 份额**: 接口报错
2. ❌ **中证指数权重**: URL 失效
3. ❌ **腾讯 K 线**: 参数错误

### 部分阻塞

4. ⚠️ **东财资金流长窗口**: lmt=500 未突破 ~6 个月

### 未完成

5. ⏸ **新浪资金定义差异**: 时间不足未测

### 建议优先级

**P0 - 立即行动**:
1. **用户本地复测东财**: 运行 `python diagnose.py`，确认 box 环境是否能连通
2. **排查上交所 headers**: 读 vibe 源码 `sources/astock_ported.py` L909-989 的实现

**P1 - 短期排查**:
3. **中证权重新 URL**: 手动访问 https://www.csindex.com.cn/ 找下载入口
4. **腾讯K线参数**: 读 vibe 源码 `sources/astock_ported.py` L467+ 的实际调用

**P2 - 评估替代**:
5. **ETF 份额**: 评估东财 `RPT_ETF_SCALE` 是否足够 (用户已有)
6. **长窗口资金流**: 如需 1 年以上，考虑其他数据源或付费接口

---

## 六、环境与依赖

### 测试环境

- **OS**: Linux 6.12.113+
- **Python**: 3.12.x
- **网络**: 云端出口 (AWS/GCP/Azure 等)
- **IP**: 非用户本地

### 依赖版本

```
requests>=2.31.0
pandas>=2.0.0
lxml>=4.9.0
openpyxl>=3.1.0
```

---

## 七、相关链接

- **PR**: https://github.com/slmyer/vibe-astock/pull/1
- **分支**: cursor/data-feasibility-smoke-48aa
- **上游静态调研**: `/home/ubuntu/.cursor/projects/workspace/uploads/repo_data_feasibility_20261109_*.{md,csv}`
- **vibe 源码基准**: commit `e0d08d19848b50d22a772729a06287cdff511629`
- **TradingAgents 基准**: commit `3a9171182304e87042743dde245c64922e04ed96`

---

## 八、免责与限制

1. ⚠️ **环境差异**: 云端成功不等于本地可用
2. ⚠️ **时间快照**: 测试时刻 2026-11-09 08:15-08:18 UTC，不保证其他时间可复现
3. ⚠️ **请求量限制**: 每接口仅 ~3 次请求，不足以证明长期稳定性
4. ⚠️ **原始限速**: ≥1s 间隔，未测试高频场景
5. ⚠️ **无绕过**: 遇验证码/封禁/限流未尝试绕过
6. ⚠️ **失败分类**: 根据表现推断，未深入排查根因

---

**交付完成时间**: 2026-11-09 08:30 UTC  
**测试者**: Cursor Cloud Agent (cursor/data-feasibility-smoke-48aa)  
**状态**: ✅ 已交付 | PR 已创建 | 等待用户本地复测
