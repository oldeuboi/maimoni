"""
Fetches the latest price for every ticker listed in tickers.json and writes
the results to prices.json. Runs server-side inside GitHub Actions, so there
are no browser CORS restrictions to work around.

Price source: Yahoo Finance's public chart endpoint (no API key required).
FX conversion: Frankfurter (European Central Bank rates, free, no key).
"""

import json
import urllib.request
import datetime

TICKERS_FILE = "tickers.json"
PRICES_FILE = "prices.json"
USER_AGENT = "Mozilla/5.0 (compatible; turto-apzvalga-price-bot/1.0)"


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_yahoo_price(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    data = fetch_json(url)
    result = data["chart"]["result"][0]
    meta = result["meta"]
    price = meta.get("regularMarketPrice")
    currency = meta.get("currency", "USD")
    if price is None:
        raise ValueError("no regularMarketPrice in response")
    return float(price), currency


def fetch_fx_rate(base, quote):
    if base == quote:
        return 1.0
    url = f"https://api.frankfurter.app/latest?from={base}&to={quote}"
    data = fetch_json(url)
    return float(data["rates"][quote])


def main():
    with open(TICKERS_FILE, "r", encoding="utf-8") as f:
        tickers = json.load(f)

    try:
        with open(PRICES_FILE, "r", encoding="utf-8") as f:
            prices = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        prices = {}

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    any_failed = False

    for symbol in tickers:
        try:
            price, currency = fetch_yahoo_price(symbol)
            rate = fetch_fx_rate(currency, "EUR")
            price_eur = round(price * rate, 4)
            prices[symbol] = {
                "symbol": symbol,
                "price": price,
                "currency": currency,
                "priceEUR": price_eur,
                "updatedAt": now,
            }
            print(f"OK   {symbol}: {price} {currency} -> {price_eur} EUR")
        except Exception as e:
            any_failed = True
            print(f"FAIL {symbol}: {e}")

    with open(PRICES_FILE, "w", encoding="utf-8") as f:
        json.dump(prices, f, indent=2, ensure_ascii=False)
        f.write("\n")

    if any_failed:
        print("Some tickers failed — see log above. prices.json still updated for the rest.")


if __name__ == "__main__":
    main()
