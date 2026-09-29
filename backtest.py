"""Backtest the retail-fade rule on data/sentiment.csv.

Rule (defaults, all adjustable):
  * Retail >= ENTRY% SHORT  -> go LONG   |  Retail >= ENTRY% LONG -> go SHORT
  * Close when long% is back within 50 +/- BAND (i.e. roughly 50/50)
  * Signals are acted on at the NEXT bar's open after the snapshot (no peeking).
  * Costs: SPREAD (in price units) charged per round trip.

Usage:
  python backtest.py --symbol XAUUSD --entry 70 --band 5 [--prices prices.csv]
Prices: hourly OHLC CSV with columns ts_utc,open,high,low,close, or omit to pull XAUUSD=X from yfinance.
"""
import argparse
import pandas as pd


def load_prices(path, symbol):
    if path:
        p = pd.read_csv(path, parse_dates=["ts_utc"])
    else:
        import yfinance as yf
        tick = {"XAUUSD": "GC=F"}.get(symbol, symbol + "=X")
        d = yf.download(tick, period="730d", interval="1h", progress=False, auto_adjust=False)
        d.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in d.columns]
        d = d.reset_index().rename(columns={d.index.name or "Datetime": "ts_utc", "index": "ts_utc"})
        p = d[["ts_utc", "open", "high", "low", "close"]]
    p["ts_utc"] = pd.to_datetime(p["ts_utc"], utc=True)
    return p.sort_values("ts_utc").reset_index(drop=True)


def run(sent, prices, entry, band, spread):
    s = sent.sort_values("ts_utc")
    s["ts_utc"] = pd.to_datetime(s["ts_utc"], utc=True)
    # act on the first price bar that opens AFTER the snapshot timestamp
    m = pd.merge_asof(s, prices, on="ts_utc", direction="forward").dropna(subset=["open"])
    pos, entry_px, trades = 0, None, []
    for _, r in m.iterrows():
        lp = r["long_pct"]
        if pos == 0:
            if lp <= 100 - entry:
                pos, entry_px, t0 = 1, r["open"], r["ts_utc"]
            elif lp >= entry:
                pos, entry_px, t0 = -1, r["open"], r["ts_utc"]
        else:
            if abs(lp - 50) <= band:
                pnl = pos * (r["open"] - entry_px) - spread
                trades.append((t0, r["ts_utc"], pos, entry_px, r["open"], pnl))
                pos = 0
    df = pd.DataFrame(trades, columns=["entry_ts", "exit_ts", "side", "entry_px", "exit_px", "pnl"])
    return df


def report(df):
    if df.empty:
        print("No completed trades yet - keep collecting."); return
    wins, losses = df[df.pnl > 0].pnl.sum(), -df[df.pnl < 0].pnl.sum()
    print(f"trades {len(df)} | win rate {(df.pnl > 0).mean():.0%} | net {df.pnl.sum():.2f} | "
          f"profit factor {wins / losses if losses else float('inf'):.2f} | avg {df.pnl.mean():.2f}")
    print(df.groupby("side").pnl.agg(["count", "sum", "mean"]))
    if len(df) < 30:
        print("WARNING: fewer than 30 trades - not statistically meaningful.")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--csv", default="data/sentiment.csv")
    a.add_argument("--symbol", default="XAUUSD")
    a.add_argument("--entry", type=float, default=70)
    a.add_argument("--band", type=float, default=5)
    a.add_argument("--spread", type=float, default=0.5)
    a.add_argument("--prices")
    a = a.parse_args()
    sent = pd.read_csv(a.csv)
    sent = sent[sent.symbol == a.symbol]
    report(run(sent, load_prices(a.prices, a.symbol), a.entry, a.band, a.spread))
