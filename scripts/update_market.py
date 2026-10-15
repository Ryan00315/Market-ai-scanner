import os
import json
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Origin": "https://tw.tradingview.com",
    "Referer": "https://tw.tradingview.com/"
}

# 1. 抓取 TradingView 台股即時全市場排行
def fetch_tw_from_tradingview():
    print("正在向 TradingView 請求台股真實排行...")
    url = "https://scanner.tradingview.com/taiwan/scan"
    payload = {
        "filter": [
            {"left": "type", "operation": "in_range", "right": ["stock", "dr"]},
            {"left": "subtype", "operation": "in_range", "right": ["common"]},
            {"left": "value", "operation": "greater", "right": 30000000} # 當日成交額大於 3000 萬台幣
        ],
        "options": {"lang": "zh_TW"},
        "columns": [
            "name",           # 代號 (如 2330)
            "description",    # 名稱 (如 台積電)
            "close",          # 現價
            "change",         # 漲跌幅 %
            "Value",          # 成交金額 (元)
            "Volatility.D"    # 當日振幅 %
        ],
        "sort": {"sortBy": "Value", "sortOrder": "desc"},
        "range": [0, 80]
    }
    try:
        res = requests.post(url, json=payload, headers=HEADERS, timeout=15)
        if res.status_code != 200:
            print(f"TradingView 回應碼異常: {res.status_code}")
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
            val_yi = round((d[4] or 0) / 100000000, 2) # 換算億元
            amp = round(d[5] or 0, 2)

            stocks.append({
                "id": sym,
                "type": "tw",
                "symbol": sym,
                "name": name,
                "price": f"{close:,.2f}",
                "change": round(pct, 2),
                "volumeVal": val_yi, # 億元
                "ampVal": amp,
                "badge": "漲停表態" if pct >= 9.5 else ("強勢突破" if pct > 3 else "常態整理"),
                "ai": {
                    "valuation": "量能充沛" if val_yi > 30 else "籌碼集中",
                    "catalyst": f"TradingView 即時成交金額達 {val_yi} 億元，當日波幅 {amp}%。",
                    "fundamentals": f"全市場即時焦點標的，成交動能維持熱絡。",
                    "bear": f"{round(close * 0.92, 1)} (-8%)",
                    "base": f"{round(close * 1.05, 1)} (+5%)",
                    "bull": f"{round(close * 1.20, 1)} (+20%)"
                }
            })
        print(f"TradingView 成功解析 {len(stocks)} 檔台股真實數據")
        return stocks
    except Exception as e:
        print(f"TradingView 抓取失敗: {e}")
        return []

# 2. 抓取加密貨幣 (幣安官方公開 API)
def fetch_crypto_real():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url, timeout=15).json()
        filtered = [
            x for x in res 
            if x['symbol'].endswith('USDT') 
            and not any(k in x['symbol'] for k in ['UP', 'DOWN', 'BEAR', 'BULL'])
            and float(x['quoteVolume']) > 8000000
        ]
        results = []
        for item in filtered:
            last = float(item['lastPrice'])
            pct = float(item['priceChangePercent'])
            high = float(item['highPrice'])
            low = float(item['lowPrice'])
            amp = (((high - low) / low) * 100) if low > 0 else 0.0
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
                "ampVal": round(amp, 2),
                "badge": "24H 波動",
                "ai": {
                    "valuation": "動能擴張" if pct > 0 else "回測整理",
                    "catalyst": f"成交額達 {vol_m} 百萬 USDT，振幅 {round(amp, 2)}%。",
                    "fundamentals": f"最高 {high}，最低 {low}。",
                    "bear": f"{round(last * 0.92, 2)} (-8%)",
                    "base": f"{round(last * 1.05, 2)} (+5%)",
                    "bull": f"{round(last * 1.25, 2)} (+25%)"
                }
            })
        return results
    except Exception:
        return []

def main():
    payload = {
        "tw": fetch_tw_from_tradingview(),
        "crypto": fetch_crypto_real(),
        "us": []
    }
    os.makedirs("data", exist_ok=True)
    with open("data/market_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("market_data.json 更新完成！")

if __name__ == "__main__":
    main()
