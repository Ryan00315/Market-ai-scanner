import os
import json
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": "https://tw.tradingview.com",
    "Referer": "https://tw.tradingview.com/"
}

# 1. 抓取【當日盤中即時真實行情】(純上市個股 TWSE，成交金額 > 3,000 萬)
def fetch_tw_live():
    print("正在抓取【當日即時盤中真實行情】...")
    url = "https://scanner.tradingview.com/taiwan/scan"
    payload = {
        "filter": [
            {"left": "type", "operation": "in_range", "right": ["stock"]},
            {"left": "subtype", "operation": "in_range", "right": ["common"]},
            {"left": "exchange", "operation": "equal", "right": "TWSE"},
            {"left": "Value", "operation": "greater", "right": 30000000}
        ],
        "options": {"lang": "zh_TW"},
        "columns": ["name", "description", "close", "change", "Value", "Volatility.D"],
        "sort": {"sortBy": "Value", "sortOrder": "desc"},
        "range": [0, 100]
    }
    try:
        res = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        if res.status_code != 200:
            print(f"TradingView 回應異常: {res.status_code}")
            return []
        data = res.json().get("data", [])
        stocks = []
        for row in data:
            d = row.get("d", [])
            if len(d) < 5 or d[2] is None or d[3] is None:
                continue
            code = str(d[0])
            name = str(d[1])
            close = float(d[2])
            change = float(d[3])
            val_yi = round((d[4] or 0) / 100000000, 2)
            amp = round(d[5] or 0, 2)

            stocks.append({
                "id": code,
                "type": "tw",
                "symbol": code,
                "name": name,
                "price": f"{close:,.2f}" if close < 100 else f"{close:,.0f}",
                "change": round(change, 2),
                "volumeVal": val_yi,
                "ampVal": amp,
                "badge": "上市即時"
            })
        print(f"當日即時上市股票共抓到 {len(stocks)} 檔")
        return stocks
    except Exception as e:
        print(f"當日即時抓取失敗: {e}")
        return []

# 2. 抓取【昨日官方正式結算行情】(台灣證交所 OpenAPI)
def fetch_tw_settlement():
    print("正在抓取【昨日證交所官方收盤結算】...")
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code != 200:
            print(f"證交所 OpenAPI 回應異常: {res.status_code}")
            return []
        data = res.json()
        stocks = []
        for row in data:
            try:
                code = str(row.get("Code", "")).strip()
                name = str(row.get("Name", "")).strip()
                if len(code) != 4 or not code.isdigit():
                    continue
                closing = float(row.get("ClosingPrice", 0) or 0)
                change = float(row.get("Change", 0) or 0)
                trade_val = float(row.get("TradeValue", 0) or 0)
                if trade_val < 30000000 or closing <= 0:
                    continue

                prev_close = closing - change
                pct = round((change / prev_close) * 100, 2) if prev_close > 0 else 0.0
                val_yi = round(trade_val / 100000000, 2)
                high = float(row.get("HighestPrice", closing) or closing)
                low = float(row.get("LowestPrice", closing) or closing)
                amp = round(((high - low) / prev_close) * 100, 2) if prev_close > 0 else 0.0

                stocks.append({
                    "id": code,
                    "type": "tw",
                    "symbol": code,
                    "name": name,
                    "price": f"{closing:,.2f}" if closing < 100 else f"{closing:,.0f}",
                    "change": pct,
                    "volumeVal": val_yi,
                    "ampVal": amp,
                    "badge": "昨日結算"
                })
            except Exception:
                continue
        stocks.sort(key=lambda x: x["volumeVal"], reverse=True)
        print(f"昨日收盤結算共抓到 {len(stocks)} 檔")
        return stocks[:100]
    except Exception as e:
        print(f"收盤結算抓取失敗: {e}")
        return []

def main():
    tw_live = fetch_tw_live()
    tw_settled = fetch_tw_settlement()

    payload = {
        "tw_live": tw_live,     # 今日盤中真實數據
        "tw": tw_settled,       # 昨日官方結算數據
        "crypto": [],
        "us": []
    }
    os.makedirs("data", exist_ok=True)
    with open("data/market_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("market_data.json 產出完畢！")

if __name__ == "__main__":
    main()
