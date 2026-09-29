# sentiment-collector

Hourly snapshots of Myfxbook community sentiment (default: XAUUSD) into `data/sentiment.csv`,
built up so the contrarian idea can be backtested later.

## Setup
1. Create a new empty GitHub repo (e.g. `sentiment-collector`) and push these files.
2. Actions tab -> `collect-sentiment` -> **Run workflow** once to test. Check that `data/sentiment.csv` gets a row.
   If it fails, the failed page is saved to `data/last_failed_XAUUSD.html` for debugging.
3. Optional: add repo secrets `MYFXBOOK_EMAIL` / `MYFXBOOK_PASSWORD` to use the official API instead of the public page.

## Notes
- Without secrets it reads the public outlook page (delayed ~60 min by Myfxbook). Check Myfxbook's terms are fine with you before leaving this running; the request rate is one page per symbol per hour.
- Change `SYMBOLS` in `collect.yml` to track more pairs.
- Wait for a few months of data before backtesting.
