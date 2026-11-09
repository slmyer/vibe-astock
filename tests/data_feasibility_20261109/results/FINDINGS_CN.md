# 数据可行性验证结果 — 独立云环境实测

**验证日期**: 2026-11-09  
**测试环境**: 独立云环境 (Cloud VM) — **结果不代表用户本地电脑可用**  
**测试方式**: 最小化HTTP请求，低请求量 (~3次/接口)，原始限速 (≥1s间隔)  
**重要声明**: 本次测试的成功/失败仅代表云端环境在测试时刻的情况，**不保证长期稳定**，也不保证在用户本地电脑上可复现。

---

## 一、核心发现汇总

### 1. 东财主力资金流 — **部分通过但窗口受限** ✓ (有限制)

**测试样本**:
- 300308 (中际旭创，深证个股)
- 515050 (科创50ETF，上交所ETF) 

**关键结论**:
- ✅ **云端能连通东财 push2his 接口**，lmt=120 和 lmt=500 均返回成功
- ⚠️ **lmt=500 并未显著扩大时间窗口**:
  - `lmt=120`: 返回 **120 条**，最早 2026-05-15 (约 **6 个月**)
  - `lmt=500`: 返回 **121 条**，最早 2026-05-14 (仅多 **1 天**)
- ⚠️ **参数 lmt 不等于返回日数**: lmt=500 不代表能取 500 个交易日
- ⚠️ **与用户本地已有的 ~121 日 (2026-05-12 起) 基本一致**，未证明能突破

**证据**:
- 详见 `evidence_normalized.csv` 行 1-4
- 原始JSON响应保存在 `test_summary.json`

**阻塞判定**:
- **不阻塞短期验证**，但 **未证明能补齐长窗口训练数据** (如需 1 年以上历史)
- 仍需在用户本地电脑或与其相同出口环境复测

---

### 2. 上交所 ETF 份额 — **失败** ✗

**测试样本**:
- 515050, 560780 (用户指定的两个上交所 ETF)

**失败原因**:
- 接口返回: `{"success":"false","error":"System Error, Please try again later..."}`
- HTTP 状态码 200 但 JSONP 内容报错

**分类**: `网络/DNS/TLS/HTTP`  
**可能原因**:
- 服务端临时故障
- 需要特殊 Referer / Cookie / 反爬验证
- API 已变更或限流

**阻塞判定**:
- **暂时阻塞**，需进一步排查 headers 或换接口
- 可参考 vibe 源码中是否有特殊处理逻辑

---

### 3. 中证指数权重 (000300) — **失败** ✗

**接口**: `https://www.csindex.com.cn/uploads/file/autofile/closeweight/000300closeweight.xls`

**失败原因**:
- 返回的是 **HTML 页面** (19KB，带 Vue 前端框架)，不是 Excel 文件
- Content-Type: `text/html` 而非 `application/vnd.ms-excel`

**分类**: `字段/日期覆盖`  
**可能原因**:
- URL 路径已失效或改版
- 需要通过网页交互下载，不支持直接URL访问
- 需要登录或 Cookie

**阻塞判定**:
- **阻塞**，当前 URL 不可用
- 需重新调研中证官网的实际下载路径或 API

---

### 4. 腾讯 K 线复权 — **失败** ✗

**测试样本**:
- sz300308 (中际旭创)
- period: day / week / month

**失败原因**:
- 接口返回: `{"code":0,"msg":"param error","data":[]}`
- HTTP 200 但业务逻辑报参数错误

**分类**: `字段/日期覆盖`  
**可能原因**:
- 腾讯接口参数格式已变更
- 代码/前缀格式不对 (sz300308 vs 其他格式)
- 接口已失效或迁移

**阻塞判定**:
- **暂时阻塞**，需重新调研腾讯K线的当前可用接口
- 可参考 vibe 源码中的实际调用参数

---

## 二、规范化数据 Schema

所有证据已整理到 `evidence_normalized.csv`，列定义如下:

| 列名 | 说明 |
|------|------|
| `test_id` | 测试序号 |
| `data_source` | 数据源标识 (如 eastmoney_fund_flow) |
| `api_endpoint` | 实际请求的域名/路径 |
| `secid_or_symbol` | 标的代码 |
| `request_param_lmt` | 请求参数 lmt (如有) |
| `request_param_period` | 请求参数 period (如有) |
| `test_env` | 测试环境 (cloud_vm / box) |
| `status` | 通过 / 失败 / 未验证 |
| `http_status_code` | HTTP 状态码 |
| `actual_rows_returned` | 实际返回行数 |
| `date_range_min` | 最早日期 |
| `date_range_max` | 最晚日期 |
| `error_category` | 失败分类 (依赖/网络/鉴权/字段/口径/历史as-of/许可未知) |
| `key_finding` | 核心发现摘要 |
| `notes` | 补充说明 |

---

## 三、环境声明与复测要求

### ⚠️ 重要: 云端成功 ≠ 本地可用

- 本次测试在 **独立云环境 (AWS/GCP 等云主机)** 进行
- 云端 IP、出口、DNS、地理位置与用户本地电脑可能不同
- **东财接口在云端通过，不等于在用户 box 上也能通过**

### 复测建议

为在用户本地电脑验证，提供独立脚本 (`/tmp/data_feasibility_test/diagnose.py`)，可在无需 clone 仓库的情况下运行:

```bash
# 仅需 requests 库
pip install requests

# 运行诊断
python diagnose.py
```

该脚本输出:
- 每个接口的 HTTP 状态码
- 实际返回内容样例
- 解析结果 (如条数、日期范围)

---

## 四、下一步建议

### 4.1 东财主力资金流

- ✅ **短期可用** (云端已验证 ~120 日)
- ⚠️ **长期窗口存疑**: lmt=500 未能突破 6 个月限制
- **TODO**: 
  1. 在用户本地电脑复测相同接口
  2. 对比 TradingAgents 的 `get_fund_flow` 实现，看是否有其他参数或分页逻辑
  3. 如确需更长历史，考虑其他数据源或付费接口

### 4.2 上交所 ETF 份额

- ❌ **当前阻塞**
- **TODO**:
  1. 检查 vibe 源码中是否有特殊 headers (Referer, Cookie 等)
  2. 尝试添加 `Referer: https://www.sse.com.cn/` 等
  3. 如仍失败，考虑改用东财 ETF 规模接口 (用户已有 em_etf_scale)

### 4.3 中证指数权重

- ❌ **当前阻塞**
- **TODO**:
  1. 访问 中证指数官网 手动下载流程，找到实际下载URL
  2. 检查是否需要 POST 请求或 Cookie
  3. 评估「最近公布快照」vs「历史 as-of 能力」

### 4.4 腾讯 K 线

- ❌ **当前阻塞**
- **TODO**:
  1. 复查 vibe 源码中腾讯K线的实际参数格式
  2. 尝试其他代码格式 (如去掉 sz 前缀)
  3. 如腾讯接口已失效，评估回退到东财或 baostock

---

## 五、artifacts 清单

为便于用户本地复测，提供以下独立文件:

1. **`requirements_minimal.txt`**: 最小依赖 (requests, pandas, lxml, openpyxl)
2. **`diagnose.py`**: 5 个接口的快速诊断脚本 (无需仓库)
3. **`smoke_test.py`**: 完整测试框架 (可复跑)
4. **`evidence_normalized.csv`**: 规范化证据表
5. **`test_summary.json`**: 完整JSON证据 (含原始响应)
6. **`FINDINGS_CN.md`**: 本报告

复跑命令:

```bash
cd /tmp/data_feasibility_test
pip install -r requirements_minimal.txt
python smoke_test.py
```

---

## 六、失败分类统计

| 分类 | 数量 | 占比 |
|------|------|------|
| 通过 | 4 | 40% |
| 失败 - 网络/DNS/TLS/HTTP | 2 | 20% |
| 失败 - 字段/日期覆盖 | 4 | 40% |
| **总计** | **10** | **100%** |

---

**报告生成时间**: 2026-11-09 08:18 UTC  
**执行环境**: Cloud Agent VM (Linux 6.12.113+, Python 3.12)  
**测试者**: Cursor Cloud Agent (cursor/data-feasibility-smoke-48aa)
