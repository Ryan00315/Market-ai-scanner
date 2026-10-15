import os
import json
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://tw.tradingview.com",
    "Referer": "https://tw.tradingview.com/"
}

# 1. 抓取 TradingView 盤中即時活躍榜
def fetch_tw_live():
    print("正在抓取【今日即時盤中】數據...")
    url = "https://scanner.tradingview.com/taiwan/scan"
    payload = {
        "filter": [
            {"left": "type", "operation": "in_range", "right": ["stock", "dr"]},
            {"left": "subtype", "operation": "in_range", "right": ["common"]},
            {"left": "value", "operation": "greater", "right": 30000000}
        ],
        "columns": ["name", "description", "close", "change", "Value", "Volatility.D"],
        "sort": {"sortBy": "Value", "sortOrder": "desc"},
        "range": [0, 40]
    }
    try:
        res = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        if res.status_code != 200:
            return []
        data = res.json().get("data", [])
        stocks = []
        for row in data:
            d = row.get("d", [])
            if len(d) < 5 or d[2] is None or d[3] is None:
                continue
            stocks.append({
                "id": str(d[0]),
                "type": "tw",
                "symbol": str(d[0]),
                "name": str(d[1]),
                "price": f"{d[2]:,.2f}",
                "change": round(d[3], 2),
                "volumeVal": round((d[4] or 0) / 100000000, 2),
                "ampVal": round(d[5] or 0, 2),
                "badge": "盤中即時"
            })
        return stocks
    except Exception as e:
        print(f"即時盤中抓取異常: {e}")
        return []

# 2. 抓取台灣證交所官方 OpenAPI【昨日收盤結算數據】
def fetch_tw_settlement():
    print("正在抓取【昨日收盤結算】數據...")
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    try:
        res = requests.get(url, timeout=15)
        if res.status_code != 200:
            return []
        data = res.json()
        stocks = []
        for row in data:
            try:
                code = row.get("Code")
                name = row.get("Name")
                closing = float(row.get("ClosingPrice", 0) or 0)
                change = float(row.get("Change", 0) or 0)
                trade_val = float(row.get("TradeValue", 0) or 0)
                
                if trade_val < 50000000 or closing <= 0:
                    continue
                
                prev_close = closing - change
                pct = round((change / prev_close) * 100, 2) if prev_close > 0 else 0.0
                val_yi = round(trade_val / 100000000, 2)
                
                stocks.append({
                    "id": str(code),
                    "type": "tw",
                    "symbol": str(code),
                    "name": str(name),
                    "price": f"{closing:,.2f}",
                    "change": pct,
                    "volumeVal": val_yi,
                    "ampVal": round(abs(pct) * 0.85, 2),
                    "badge": "昨日收盤"
                })
            except Exception:
                continue
        stocks.sort(key=lambda x: x["volumeVal"], reverse=True)
        return stocks[:40]
    except Exception as e:
        print(f"收盤結算抓取異常: {e}")
        return []

def main():
    tw_live = fetch_tw_live()
    tw_settled = fetch_tw_settlement()

    payload = {
        "tw_live": tw_live,
        "tw": tw_settled,
        "crypto": [],
        "us": []
    }
    os.makedirs("data", exist_ok=True)
    with open("data/market_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("market_data.json 更新完成！")

if __name__ == "__main__":
    main()
