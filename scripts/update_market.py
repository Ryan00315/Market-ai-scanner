import os
import json
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 抓取台灣證交所官方每日收盤行情 (依成交值篩選)
def fetch_tw_post_market():
    print("正在抓取台灣證交所官方每日收盤排行...")
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

            # 只取 4 碼上市公司普通股
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
                vol_yi = round(trade_value / 100000000, 2) # 成交金額換算為「億元」

                # 關鍵篩選：當日成交金額大於 2,000 萬元才進入排行候選，排除死魚股
                if vol_yi > 0.2:
                    all_stocks.append({
                        "id": code,
                        "type": "tw",
                        "symbol": code,
                        "name": name,
                        "price": f"{close_price:,.2f}",
                        "change": round(pct, 2),
                        "volumeVal": vol_yi, # 億元
                        "ampVal": round(amp, 2),
                        "badge": "漲停強勢" if pct >= 9.5 else ("突破整理" if pct > 3 else "常態震盪"),
                        "ai": {
                            "valuation": "動能突破" if pct > 5 else ("破線尋底" if pct < -4 else "合理估值"),
                            "catalyst": f"全市場盤後正式成交額達 {vol_yi} 億元，當日波幅 {round(amp, 2)}%。",
                            "fundamentals": f"最高 {high_price:,.2f}，最低 {low_price:,.2f}，量能充足。",
                            "bear": f"{round(close_price * 0.92, 1)} (-8%)",
                            "base": f"{round(close_price * 1.05, 1)} (+5%)",
                            "bull": f"{round(close_price * 1.20, 1)} (+20%)"
                        }
                    })
            except Exception:
                continue

        # 依成交量條件排序出各大前 15 名
        top_gainers = sorted(all_stocks, key=lambda x: x['change'], reverse=True)[:15]
        top_losers = sorted(all_stocks, key=lambda x: x['change'])[:15]
        top_volume = sorted(all_stocks, key=lambda x: x['volumeVal'], reverse=True)[:25]
        top_amplitude = sorted(all_stocks, key=lambda x: x['ampVal'], reverse=True)[:15]

        combined = {item['id']: item for item in (top_gainers + top_losers + top_volume + top_amplitude)}
        print(f"台股官方盤後結算完成，共納入 {len(combined)} 檔熱門標的")
        return list(combined.values())
    except Exception as e:
        print(f"證交所 API 抓取失敗: {e}")
        return []

def main():
    payload = {
        "tw": fetch_tw_post_market(),
        "crypto": [],
        "us": []
    }
    os.makedirs("data", exist_ok=True)
    with open("data/market_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print("data/market_data.json 更新完成！")

if __name__ == "__main__":
    main()
