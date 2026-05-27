# sg-dividend-data

Daily ETL that scrapes SGX dividend stocks and emits `sg_dividend_universe.json` to a Cloudflare R2 bucket. Consumed by the SG Dividend Optimizer mobile app.

## Run locally
```
pip install -e ".[dev]"
sg-dividend-refresh --dry-run     # writes to ./sg_dividend_universe.json
sg-dividend-refresh               # uploads to R2 (requires env vars)
```

## Required env vars
- `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (optional, for failure alerts)
