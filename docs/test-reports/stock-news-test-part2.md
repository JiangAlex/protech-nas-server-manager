# ProTech-Stock-News 功能測試結果 — Part 2

**測試日期**: 2026-08-19  
**測試者**: QA (qa profile)  
**API Base**: http://localhost:8020

---

## 1. 美股指數 K 線 — 道瓊(^DJI)/那斯達克(^IXIC)/費城半導體(^SOX)

**端點**: `GET /api/usindex/{symbol}/kline?period=daily&days=30`

| Symbol | 狀態 | 說明 |
|--------|------|------|
| ^DJI   | ✅ 正常 | 30筆日K資料，open/high/low/close/vol 全數有值 |
| ^IXIC  | ✅ 正常 | 30筆日K資料，open/high/low/close/vol 全數有值 |
| ^SOX   | ⚠️ 資料異常 | 30筆日K資料，但 **volume 全為 0**（Yahoo Finance 資料源問題） |

**請求**:
```bash
curl "http://localhost:8020/api/usindex/%5EDJI/kline?period=daily&days=30"
curl "http://localhost:8020/api/usindex/%5EIXIC/kline?period=daily&days=30"
curl "http://localhost:8020/api/usindex/%5ESOX/kline?period=daily&days=30"
```

**Bug 記錄**:  
- SOX volume=0 → Yahoo Finance 對 SOX 指数不提供成交量，建議前端的 chart_service.py 取不到 volume 時改顯示「成交量暫無資料」而非顯示 0。

---

## 2. 社群爆紅榜 (hot_search / most_watched / most_gainer)

**端點**: `GET /api/hot-stocks?type=hot_search|most_watched|most_gainer`

| type | 狀態 | 說明 |
|------|------|------|
| hot_search  | ❌ 空陣列 `[]` | Yahoo 社群排名頁面結構可能已變更 |
| most_watched | ❌ 空陣列 `[]` | 同上 |
| most_gainer | ❌ 空陣列 `[]` | 同上 |

**請求**:
```bash
curl "http://localhost:8020/api/hot-stocks?type=hot_search"
curl "http://localhost:8020/api/hot-stocks?type=most_watched"
curl "http://localhost:8020/api/hot-stocks?type=most_gainer"
```

**根因分析** (`src/services/yahoo_service.py`):
```python
BASE_URL = "https://tw.stock.yahoo.com"
def fetch_hot_stocks(rank_type="active"):
    resp = requests.get(f"{BASE_URL}/community/rank/{rank_type}", ...)
    if resp.status_code != 200:
        return []
```
Yahoo 社群排名 URL `/community/rank/{rank_type}` 可能已不存在或返回非 200。

**Bug 記錄**: hot-stocks 三種排序全部回傳空陣列，需更新 Yahoo 社群排名解析邏輯或更換資料源。

---

## 3. 漲跌幅排行（上市/上櫃/漲幅/跌幅）

**端點**: `GET /api/rank?direction=up|down&market=上市|%E4%B8%8A%E5%B8%82`

| 測試場景 | 狀態 | 說明 |
|----------|------|------|
| market=上市（URL-Encode） | ✅ 正常 | 有回傳100筆，但**混入了上櫃股票**（market 參數未生效） |
| market=上市（Raw UTF-8） | ❌ Bug | `Invalid HTTP request received.` — FastAPI/Uvicorn 無法解析原始 UTF-8 |
| market=上櫃（URL-Encode） | ⚠️ 異常 | 同樣混入上市股票，filter 未生效 |
| direction=up（漲幅） | ✅ 正常 | 有回傳100筆 |
| direction=down（跌幅） | ✅ 正常 | 有回傳100筆 |

**請求**:
```bash
# Bug: raw UTF-8 causes HTTP error
curl "http://localhost:8020/api/rank?direction=up&market=上市"

# 正常（但 market 參數未生效）
curl "http://localhost:8020/api/rank?direction=up&market=%E4%B8%8A%E5%B8%82"
```

**Bug 記錄**:
1. **market 參數 URL-Encode Bug**: 原始 UTF-8 `market=上市` 導致 HTTP 解析錯誤，前端必須確保 URL-encode
2. **market 參數無效**: URL-encode 後的 `market=%E4%B8%8A%E5%B8%82` 不會過濾上櫃股票，顯示結果混雜，建議檢查 `fetch_rank()` 的 market 參數處理邏輯

---

## 4. 每日財經新聞（鉅亨網/Yahoo奇摩股市/CMoney）

**說明**: 新聞模組為排程制（每小時自動抓取 → Telegram 推播），無 REST API endpoint `GET /api/news`（已確認回傳 404）。

| 來源 | 測試方式 | 狀態 | 說明 |
|------|----------|------|------|
| 鉅亨網 (Anue) | 直接 curl API | ✅ 正常 | `https://api.cnyes.com/media/api/v1/newslist/category/headline?limit=3` 回傳 JSON |
| Yahoo奇摩股市 | BeautifulSoup 爬蟲 | ⚠️ 待確認 | 網頁可能已改版，需驗證解析邏輯是否仍適用 |
| CMoney | 替代方案 | ✅ 已實作 | CMoney 需登入，`finance_news.py` 已使用 Anue tw_stock_news 作為替代 |

**驗證方式**:
```bash
# 鉅亨網 — 確認有回應
curl -s "https://api.cnyes.com/media/api/v1/newslist/category/headline?limit=3"
```

**建議**: 前端或文件應說明「每日財經新聞」無獨立 API，需透過 Telegram Bot 接收，或提供 `GET /api/news` endpoint 直接取得最新快取結果。

---

## 摘要

| # | 測項 | 結果 |
|---|------|------|
| 1 | 美股指數 K 線（DJI/IXIC/SOX） | ⚠️ SOX volume=0 |
| 2 | 社群爆紅榜（3種排序） | ❌ 全部回傳空陣列 |
| 3 | 漲跌幅排行 market 參數 | ❌ URL-encode bug + filter 無效 |
| 4 | 每日財經新聞抓取 | ⚠️ 無 REST API，需補 endpoint 或更新文件 |

## 改善建議

1. **hot-stocks 空陣列**: 重新確認 Yahoo 社群排名的 URL 與回傳格式，必要时更換為 Yahoo Finance Quote 的其他 API
2. **SOX volume=0**: 前端 `chart_service.py` 對 volume=0 應顯示「暫無資料」而非 0
3. **rank market 參數**: 確認 `fetch_rank()` 中 market 的比對邏輯（現在看起來所有市場混在一起）
4. **news API**: 提供 `GET /api/news` endpoint，讓使用者可直接查詢最新抓取的新聞，而非完全依賴 Telegram
