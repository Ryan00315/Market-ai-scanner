import os
import json
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# ================= 1. 加密貨幣：全市場動態排行 (Binance) =================
def fetch_crypto_real_market():
    print("正在掃描加密貨幣全市場動態排行...")
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        res = requests.get(url, timeout=15).json()

        # 過濾 USDT 交易對，排除槓桿代幣 (UP/DOWN/BULL/BEAR)
        filtered = [
            x for x in res 
            if x['symbol'].endswith('USDT') 
            and not any(k in x['symbol'] for k in ['UP', 'DOWN', 'BEAR', 'BULL'])
            and float(x['quoteVolume']) > 5000000 # 24H成交金額大於 500 萬美元
        ]

        all_crypto = []
        for item in filtered:
            last = float(item['lastPrice'])
            pct = float(item['priceChangePercent'])
            high = float(item['highPrice'])
            low = float(item['lowPrice'])
            amp = (((high - low) / low) * 100) if low > 0 else 0.0
            vol_m = round(float(item['quoteVolume']) / 1000000, 1) # 百萬 USDT
            clean_sym = item['symbol'].replace('USDT', '')

            all_crypto.append({
                "id": item['symbol'],
                "type": "crypto",
                "symbol": clean_sym,
                "name": clean_sym,
                "price": f"{last:,.2f}" if last >= 1 else str(last),
                "change": round(pct, 2),
                "volumeVal": vol_m,
                "ampVal": round(amp, 2),
                "badge": "突破爆量" if pct > 5 else ("回檔修正" if pct < -5 else "區間整理"),
                "ai": {
                    "valuation": "強勢動能" if pct > 0 else "回測整理",
                    "catalyst": f"24H 全網成交金額達 {vol_m} 百萬 USDT，市場關注度高。",
                    "fundamentals": f"24H 最高 {high}，最低 {low}，波幅 {round(amp, 2)}%。",
                    "bear": f"{round(last * 0.92, 2)} (-8%)",
                    "base": f"{round(last * 1.05, 2)} (+5%)",
                    "bull": f"{round(last * 1.25, 2)} (+25%)"
                }
            })

        # 取各排行前 12 名聯集
        top_gainers = sorted(all_crypto, key=lambda x: x['change'], reverse=True)[:15]
        top_losers = sorted(all_crypto, key=lambda x: x['change'])[:15]
        top_volume = sorted(all_crypto, key=lambda x: x['volumeVal'], reverse=True)[:20]
        top_amplitude = sorted(all_crypto, key=lambda x: x['ampVal'], reverse=True)[:15]

        combined = {item['id']: item for item in (top_gainers + top_losers + top_volume + top_amplitude)}
        print(f"加密貨幣全市場動態排行完成，共取 {len(combined)} 檔熱門標的")
        return list(combined.values())
    except Exception as e:
        print(f"加密貨幣 API 抓取失敗: {e}")
        return []

# ================= 2. 台股：全市場動態排行 (台灣證交所官方 OpenAPI) =================
def fetch_tw_real_market():
    print("正在掃描台灣證交所全市場動態排行...")
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        data = res.json()

        all_stocks = []
        for s in data:
            code = s.get('Code', '')
            name = s.get('Name', '')
            close_str = s.get('ClosingPrice', '').replace(',', '')
            change_str = s.get('Change', '').replace(',', '')
            trade_val_str = s.get('TradeValue', '').replace(',', '')
            high_str = s.get('HighestPrice', '').replace(',', '')
            low_str = s.get('LowestPrice', '').replace(',', '')

            # 只取 4 碼上市普通股
            if len(code) != 4 or not code.isdigit():
                continue
            if not close_str or close_str == '--':
                continue

            try:
                close_price = float(close_str)
                change_val = float(change_str) if change_str and change_str != '--' else 0.0
                trade_value = float(trade_val_str) if trade_val_str else 0.0
                high_price = float(high_str) if high_str and high_str != '--' else close_price
                low_price = float(low_str) if low_str and low_str != '--' else close_price
                
                prev_close = close_price - change_val
                pct = ((close_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
                amp = (((high_price - low_price) / prev_close) * 100) if prev_close > 0 else 0.0
                vol_yi = round(trade_value / 100000000, 2) # 成交金額：換算為「億元」

                # 當日成交額大於 2,000 萬元才進入排行篩選
                if vol_yi > 0.2:
                    all_stocks.append({
                        "id": code,
                        "type": "tw",
                        "symbol": code,
                        "name": name,
                        "price": f"{close_price:,.2f}",
                        "change": round(pct, 2),
                        "volumeVal": vol_yi,
                        "ampVal": round(amp, 2),
                        "badge": "漲停表態" if pct >= 9.5 else ("強勢突破" if pct > 3 else "常態震盪"),
                        "ai": {
                            "valuation": "動能突破" if pct > 5 else ("破線尋底" if pct < -4 else "合理估值"),
                            "catalyst": f"全市場當日成交金額達 {vol_yi} 億元，波幅 {round(amp, 2)}%。",
                            "fundamentals": f"最高 {high_price:,.2f}，最低 {low_price:,.2f}，多空量能激戰。",
                            "bear": f"{round(close_price * 0.92, 1)} (-8%)",
                            "base": f"{round(close_price * 1.05, 1)} (+5%)",
                            "bull": f"{round(close_price * 1.20, 1)} (+20%)"
                        }
                    })
            except Exception:
                continue

        top_gainers = sorted(all_stocks, key=lambda x: x['change'], reverse=True)[:15]
        top_losers = sorted(all_stocks, key=lambda x: x['change'])[:15]
        top_volume = sorted(all_stocks, key=lambda x: x['volumeVal'], reverse=True)[:25]
        top_amplitude = sorted(all_stocks, key=lambda x: x['ampVal'], reverse=True)[:15]

        combined = {item['id']: item for item in (top_gainers + top_losers + top_volume + top_amplitude)}
        print(f"台股全市場動態排行完成，共取 {len(combined)} 檔標的")
        return list(combined.values())
    except Exception as e:
        print(f"證交所 API 讀取異常: {e}")
        return []

# ================= 3. 美股：全市場動態排行 (Yahoo Finance Screener) =================
def fetch_us_real_market():
    print("正在掃描美股全市場動態排行 (Gainers, Losers, Actives)...")
    # 分別請求當日全美股「漲幅榜」、「跌幅榜」與「成交最活躍榜」
    endpoints = {
        "gainers": "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?formatted=false&scrIds=day_gainers&count=25",
        "losers": "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?formatted=false&scrIds=day_losers&count=25",
        "actives": "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved?formatted=false&scrIds=most_actives&count=30"
    }

    all_us = {}

    for category, url in endpoints.items():
        try:
            res = requests.get(url, headers=HEADERS, timeout=15)
            if res.status_code == 200:
                quotes = res.json().get('finance', {}).get('result', [{}])[0].get('quotes', [])
                for q in quotes:
                    sym = q.get('symbol', '')
                    name = q.get('shortName', sym)
                    price = q.get('regularMarketPrice', 0.0)
                    pct = q.get('regularMarketChangePercent', 0.0)
                    vol = q.get('regularMarketVolume', 0)
                    high = q.get('regularMarketDayHigh', price)
                    low = q.get('regularMarketDayLow', price)

                    # 排除低於 1 美元之便士股以提升數據品質
                    if price < 1.0 or not sym:
                        continue

                    amp = (((high - low) / low) * 100) if low > 0 else 0.0
                    vol_val_b = round((price * vol) / 100000000, 2) # 成交金額：換算為「億美元」

                    all_us[sym] = {
                        "id": sym,
                        "type": "us",
                        "symbol": sym,
                        "name": name,
                        "price": f"{price:,.2f}",
                        "change": round(pct, 2),
                        "volumeVal": vol_val_b,
                        "ampVal": round(amp, 2),
                        "badge": "漲幅榜" if category == "gainers" else ("跌幅榜" if category == "losers" else "人氣核心"),
                        "ai": {
                            "valuation": "動能強勢" if pct > 0 else "空方壓制",
                            "catalyst": f"全美股活躍榜標的，當日成交規模達 {vol_val_b} 億美元。",
                            "fundamentals": f"日內高點 {high:,.2f}，低點 {low:,.2f}，波幅 {round(amp, 2)}%。",
                            "bear": f"{round(price * 0.90, 2)} (-10%)",
                            "base": f"{round(price * 1.06, 2)} (+6%)",
                            "bull": f"{round(price * 1.25, 2)} (+25%)"
                        }
                    }
        except Exception as e:
            print(f"美股 {category} 抓取異常: {e}")

    print(f"美股全市場動態排行完成，共取 {len(all_us)} 檔當日焦點標的")
    return list(all_us.values())

def main():
    print("=== 開始執行全市場即時排行榜聚合 ===")
    payload = {
        "crypto": fetch_crypto_real_market(),
        "tw": fetch_tw_real_market(),
        "us": fetch_us_real_market()
    }
    os.makedirs("data", exist_ok=True)
    with open("data/market_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("=== 聚合完成！data/market_data.json 已更新 ===")

if __name__ == "__main__":
    main()
