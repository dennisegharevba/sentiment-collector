"""Hourly Myfxbook community-outlook snapshot -> data/sentiment.csv

Mode 1 (preferred, if MYFXBOOK_EMAIL / MYFXBOOK_PASSWORD are set): official API.
Mode 2 (no API access needed): read the public outlook page for each symbol.
Public data is delayed ~60 min by Myfxbook, so rows are stamped with fetch time in UTC.
"""
import csv, os, re, sys, time, datetime as dt
import requests

SYMBOLS = [s.strip().upper() for s in os.getenv("SYMBOLS", "XAUUSD").split(",") if s.strip()]
OUT = "data/sentiment.csv"
FIELDS = ["ts_utc", "symbol", "long_pct", "short_pct", "long_lots", "short_lots",
          "long_positions", "short_positions", "source"]
UA = {"User-Agent": "Mozilla/5.0 (research; hourly snapshot; contact via repo owner)"}


def num(s):
    return float(s.replace(",", ""))


def from_api():
    email, pw = os.getenv("MYFXBOOK_EMAIL"), os.getenv("MYFXBOOK_PASSWORD")
    if not (email and pw):
        return None
    r = requests.get("https://www.myfxbook.com/api/login.json",
                     params={"email": email, "password": pw}, timeout=30).json()
    if r.get("error"):
        raise RuntimeError(f"login failed: {r.get('message')}")
    sess = r["session"]
    d = requests.get("https://www.myfxbook.com/api/get-community-outlook.json",
                     params={"session": sess}, timeout=30).json()
    rows = []
    for s in d.get("symbols", []):
        if s["name"].upper() in SYMBOLS:
            rows.append([s["name"].upper(), s["longPercentage"], s["shortPercentage"],
                         s["longVolume"], s["shortVolume"],
                         s["longPositions"], s["shortPositions"], "api"])
    requests.get("https://www.myfxbook.com/api/logout.json", params={"session": sess}, timeout=30)
    return rows


def parse_page(html):
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    pct = re.findall(r"(\d{1,3}(?:\.\d+)?)\s*%", text)
    lots = re.findall(r"([\d,]+(?:\.\d+)?)\s*lots", text, re.I)
    pos = re.findall(r"([\d,]+)\s*positions", text, re.I)
    if len(pct) < 2 or len(lots) < 2 or len(pos) < 2:
        raise ValueError("could not find long/short figures")
    lp, sp = float(pct[0]), float(pct[1])
    if not 98 <= lp + sp <= 102:
        raise ValueError(f"percentages do not sum to ~100 ({lp}+{sp})")
    return [lp, sp, num(lots[0]), num(lots[1]), num(pos[0]), num(pos[1])]


def from_page():
    rows = []
    for sym in SYMBOLS:
        url = f"https://www.myfxbook.com/community/outlook/{sym}"
        resp = requests.get(url, headers=UA, timeout=30)
        try:
            resp.raise_for_status()
            rows.append([sym, *parse_page(resp.text), "page"])
        except Exception as e:
            os.makedirs("data", exist_ok=True)
            open(f"data/last_failed_{sym}.html", "w", encoding="utf-8").write(resp.text)
            print(f"{sym}: {e}", file=sys.stderr)
        time.sleep(3)
    return rows


def main():
    rows = from_api() or from_page()
    if not rows:
        sys.exit("no rows collected")
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new = not os.path.exists(OUT)
    os.makedirs("data", exist_ok=True)
    with open(OUT, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(FIELDS)
        for r in rows:
            w.writerow([ts, *r])
    print(f"wrote {len(rows)} row(s) at {ts}")


if __name__ == "__main__":
    main()
