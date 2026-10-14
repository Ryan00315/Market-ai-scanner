import os
import json
import requests
import yfinance as yf
from google import genai

AI_KEY = os.environ.get("AI_API_KEY")

def get_crypto_data():
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    results = []
    for s in symbols:
        try:
            r = requests.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={s}", timeout=10).json()
            results.append({
                "id": s,
                "type": "crypto",
                "symbol": s.replace("USDT", " / USDT"),
                "name": "比特幣" if "BTC" in s else ("以太坊" if "ETH" in s else "Solana"),
                "price": f"{float(r['lastPrice']):,.2f}",
                "change": f"{float(r['priceChangePercent']):+.2f}%",
                "isUp": float(r['priceChangePercent']) >= 0,
                "badge": "24H 波動"
            })
        except Exception as e:
            print(f"Error fetching {s}: {e}")
    return results

def get_stock_data(tickers, market_type):
    results = []
    for code, name in tickers.items():
        try:
            ticker = yf.Ticker(code)
            hist = ticker.history(period="2d")
            if len(hist) >= 2:
                prev = hist['Close'].iloc[-2]
                curr = hist['Close'].iloc[-1]
                pct = ((curr - prev) / prev) * 100
                clean_symbol = code.replace(".TW", "")
                results.append({
                    "id": clean_symbol,
                    "type": market_type,
                    "symbol": clean_symbol,
                    "name": name,
                    "price": f"{curr:,.2f}",
                    "change": f"{pct:+.2f}%",
                    "isUp": pct >= 0,
                    "badge": "日線走勢"
                })
        except Exception as e:
            print(f"Error fetching {code}: {e}")
    return results

def analyze_with_ai(client, item):
    prompt = f"""
    標的：{item['name']} ({item['symbol']})，現價：{item['price']}，漲跌：{item['change']}。
    請以專業客觀的量化分析師視角，用繁體中文輸出以下純 JSON 格式（不要使用任何 Markdown 格式或額外文字）：
    {{
      "valuation": "合理偏低 / 偏高 / 動能擴張 (簡述原因)",
      "catalyst": "100字內催化因素與營收/消息重點",
      "fundamentals": "100字內財務或籌碼觀察",
      "bear": "保守價 (跌幅%)",
      "base": "中性價 (漲跌%)",
      "bull": "樂觀價 (漲幅%)"
    }}
    """
    try:
        res = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return json.loads(res.text.strip('`json\n '))
    except Exception:
        return {
            "valuation": "動能觀察中",
            "catalyst": "市場流動性健康，技術均線整理中。",
            "fundamentals": "成交量維持健康水位。",
            "bear": "支撐區間",
            "base": "震盪整理",
            "bull": "目標價位"
        }

def main():
    client = genai.Client(api_key=AI_KEY) if AI_KEY else None

    tw_list = get_stock_data({"2330.TW": "台積電", "2345.TW": "智邦", "2454.TW": "聯發科"}, "tw")
    us_list = get_stock_data({"NVDA": "NVIDIA", "AAPL": "Apple", "TSLA": "Tesla"}, "us")
    crypto_list = get_crypto_data()

    if client:
        for item in crypto_list + tw_list + us_list:
            item["ai"] = analyze_with_ai(client, item)

    payload = { "crypto": crypto_list, "tw": tw_list, "us": us_list }
    os.makedirs("data", exist_ok=True)
    with open("data/market_data.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
