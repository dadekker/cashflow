from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
import yfinance as yf
from .models import Holding, PriceCache, FxCache

PRICE_TTL = timedelta(minutes=15)
FX_TTL = timedelta(hours=6)
BASE = "AUD"
FX_TICKERS = {"USD": "AUDUSD=X", "EUR": "EURAUD=X"}


def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def infer_currency(ticker: str, fallback: str) -> str:
    suffix = ticker.upper().split(".")[-1] if "." in ticker else ""
    if suffix == "AX": return "AUD"
    if suffix in {"AS", "DE", "PA", "MI", "MC", "BR", "LS"}: return "EUR"
    return fallback


def fetch_quote(ticker: str, fallback_currency: str) -> tuple[float, str, datetime]:
    t = yf.Ticker(ticker)
    info = {}
    try:
        info = t.fast_info or {}
    except Exception:
        info = {}
    price = info.get("last_price") or info.get("regular_market_price")
    currency = info.get("currency") or infer_currency(ticker, fallback_currency)
    if not price:
        hist = t.history(period="5d", interval="1d")
        if hist.empty:
            raise RuntimeError(f"No price returned for {ticker}")
        price = float(hist["Close"].dropna().iloc[-1])
    return float(price), currency.upper(), now_utc()


def refresh_price(db: Session, ticker: str, fallback_currency: str, force: bool = False) -> PriceCache | None:
    cached = db.get(PriceCache, ticker)
    if cached and not force and cached.as_of > now_utc() - PRICE_TTL:
        return cached
    try:
        price, currency, as_of = fetch_quote(ticker, fallback_currency)
        cached = cached or PriceCache(ticker=ticker, price=price, currency=currency, as_of=as_of)
        cached.price = price; cached.currency = currency; cached.as_of = as_of
        db.merge(cached); db.commit()
        return db.get(PriceCache, ticker)
    except Exception:
        return cached


def fetch_fx_rate(currency: str) -> tuple[float, datetime]:
    if currency == BASE:
        return 1.0, now_utc()
    ticker = FX_TICKERS[currency]
    t = yf.Ticker(ticker)
    price = None
    try:
        price = (t.fast_info or {}).get("last_price")
    except Exception:
        pass
    if not price:
        hist = t.history(period="5d", interval="1d")
        if hist.empty:
            raise RuntimeError(f"No FX rate returned for {ticker}")
        price = float(hist["Close"].dropna().iloc[-1])
    if currency == "USD":
        # AUDUSD = USD per AUD, so USD -> AUD is reciprocal.
        price = 1 / float(price)
    return float(price), now_utc()


def refresh_fx(db: Session, currency: str, force: bool = False) -> FxCache | None:
    if currency == BASE:
        return FxCache(pair="AUDAUD", rate=1.0, as_of=now_utc())
    pair = f"{currency}AUD"
    cached = db.get(FxCache, pair)
    if cached and not force and cached.as_of > now_utc() - FX_TTL:
        return cached
    try:
        rate, as_of = fetch_fx_rate(currency)
        cached = cached or FxCache(pair=pair, rate=rate, as_of=as_of)
        cached.rate = rate; cached.as_of = as_of
        db.merge(cached); db.commit()
        return db.get(FxCache, pair)
    except Exception:
        return cached


def portfolio_summary(db: Session, force: bool = False) -> dict:
    holdings = db.query(Holding).order_by(Holding.ticker).all()
    rows = []
    total_value_aud = total_cost_aud = 0.0
    for h in holdings:
        price = refresh_price(db, h.ticker, h.currency, force=force)
        fx = refresh_fx(db, h.currency, force=force)
        current = price.price if price else None
        fx_rate = fx.rate if fx else (1.0 if h.currency == BASE else None)
        native_value = current * h.shares if current is not None else None
        native_cost = h.cost_per_share * h.shares
        value_aud = native_value * fx_rate if native_value is not None and fx_rate is not None else None
        cost_aud = native_cost * fx_rate if fx_rate is not None else None
        pl_aud = value_aud - cost_aud if value_aud is not None and cost_aud is not None else None
        pl_pct = (pl_aud / cost_aud * 100) if pl_aud is not None and cost_aud else None
        if value_aud is not None: total_value_aud += value_aud
        if cost_aud is not None: total_cost_aud += cost_aud
        rows.append({
            "id": h.id, "ticker": h.ticker, "shares": h.shares, "cost_per_share": h.cost_per_share,
            "currency": h.currency, "current_price": current, "price_as_of": price.as_of.isoformat() if price else None,
            "fx_rate_to_aud": fx_rate, "fx_as_of": fx.as_of.isoformat() if fx else None,
            "market_value_native": native_value, "cost_basis_native": native_cost,
            "market_value_aud": value_aud, "cost_basis_aud": cost_aud,
            "pl_aud": pl_aud, "pl_pct": pl_pct, "weight_pct": 0,
        })
    for row in rows:
        row["weight_pct"] = (row["market_value_aud"] / total_value_aud * 100) if row["market_value_aud"] and total_value_aud else 0
    pl = total_value_aud - total_cost_aud
    return {"totals": {"market_value_aud": total_value_aud, "cost_basis_aud": total_cost_aud, "pl_aud": pl, "pl_pct": (pl / total_cost_aud * 100) if total_cost_aud else 0}, "holdings": rows}
