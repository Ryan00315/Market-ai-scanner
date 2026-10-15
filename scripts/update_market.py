import os
import json
import requests
import yfinance as yf
from datetime import datetime, timedelta

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": "https://tw.tradingview.com",
    "Referer": "https://tw.tradingview.com/"
}

def fetch_tw_live_tradingview():
    print("正在向 TradingView 抓取台股即時排行榜...")
    url = "https://scanner.tradingview.com/taiwan/scan"
    payload = {
        "filter": [
            {"left": "type", "operation": "in_range", "right": ["stock", "dr"]},
            {"left": "subtype", "operation": "in_range", "right": ["common"]},
            {"left": "value", "operation": "greater", "right": 30000000}
        ],
        "options": {"lang": "zh_TW"},
        "columns": [
            "name",
            "description",
            "close",
            "change",
            "Value",
            "Volatility.D"
        ],
        "sort": {"sortBy": "Value", "sortOrder": "desc"},
        "range": [0, 40]  # 取得前 40 檔核心成交熱門股
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

            sym = d[0]
            name = d[1]
            close = d[2]
            pct = d[3]
            val_yi = round((d[4] or 0) / 100000000, 2)
            amp = round(d[5] or 0, 2)

            stocks.append({
                "id": sym,
                "type": "tw",
                "symbol": sym,
                "name": name,
                "price": f"{close:,.2f}",
                "change": round(pct, 2),
                "volumeVal": val_yi,
                "ampVal": amp,
                "history": [] # 稍後填入真實 K 棒
            })
        return stocks
    except Exception as e:
        print(f"TradingView 抓取失敗: {e}")
        return []

# 為進榜個股批次抓取真實歷史走勢 (近 90 天)
def enrich_with_real_history(stocks):
    if not stocks:
        return stocks
    print(f"開始為 {len(stocks)} 檔標的下載真實 K 棒數據...")
    tickers = [f"{s['symbol']}.TW" for s in stocks]
    
    try:
        # 一次批次下載，節省時間與額度
        data = yf.download(tickers, period="3mo", interval="1d", group_by='ticker', progress=False)
        
        for s in stocks:
            sym_tw = f"{s['symbol']}.TW"
            try:
                df = data[sym_tw] if len(stocks) > 1 else data
                df = df.dropna()
                candles = []
                for index, row in df.iterrows():
                    candles.append({
                        "time": index.strftime("%Y-%m-%d"),
                        "open": round(float(row['Open']), 2),
                        "high": round(float(row['High']), 2),
                        "low": round(float(row['Low']), 2),
                        "close": round(float(row['Close']), 2),
                        "volume": int(row['Volume'])
                    })
                s["history"] = candles
            except Exception:
                s["history"] = []
    except Exception as e:
        print(f"yfinance 抓取歷史 K 棒失敗: {e}")
        
    return stocks

def fetch_crypto_real():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url, timeout=15).json()
        filtered = [
            x for x in res 
            if x['symbol'].endswith('USDT') 
            and not any(k in x['symbol'] for k in ['UP', 'DOWN', 'BEAR', 'BULL'])
            and float(x['quoteVolume']) > 8000000
        ][:30]
        results = []
        for item in filtered:
            last = float(item['lastPrice'])
            pct = float(item['priceChangePercent'])
            vol_m = round(float(item['quoteVolume']) / 1000000, 1)
            sym = item['symbol'].replace('USDT', '')
            results.append({
                "id": item['symbol'],
                "type": "crypto",
                "symbol": sym,
                "name": sym,
                "price": f"{last:,.2f}" if last >= 1 else str(last),
                "change": round(pct, 2),
                "volumeVal": vol_m,
                "ampVal": 4.5,
                "history": []
            })
        return results
    except Exception:
        return []

def main():
    tw_stocks = fetch_tw_live_tradingview()
    tw_stocks_with_candles = enrich_with_real_history(tw_stocks)

    payload = {
        "tw_live": tw_stocks_with_candles,
        "tw": tw_stocks_with_candles,
        "crypto": fetch_crypto_real(),
        "us": []
    }
    os.makedirs("data", exist_ok=True)
    with open("data/market_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("data/market_data.json 包含真實歷史 K 棒產出完畢！")

if __name__ == "__main__":
    main()
