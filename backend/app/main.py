import os
from datetime import date, timedelta
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from .database import Base, engine, get_db, SessionLocal
from .models import Anchor, Cashflow, Holding, WebAuthnCredential
from .schemas import AnchorIn, AnchorOut, CashflowIn, CashflowOut, HoldingIn, HoldingOut, OverwriteIn, CredentialNameIn
from .cashflow import calculated_balance, forecast as build_forecast
from .portfolio import portfolio_summary
from .auth import current_user, has_credentials, registration_options, verify_registration, authentication_options, verify_authentication, clear_session

app = FastAPI(title="Personal Cashflow & Portfolio Dashboard")
app.add_middleware(CORSMiddleware, allow_origins=[os.getenv("WEBAUTHN_ORIGIN", "https://cash.daviddekker.com"), "http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def seed_demo(db: Session):
    if db.query(Anchor).count() or os.getenv("SEED_DEMO", "false").lower() != "true":
        return
    today = date.today()
    db.add(Anchor(date=today.isoformat(), amount=7250, note="Demo starting balance"))
    db.add_all([
        Cashflow(label="Salary", amount=3200, direction="income", kind="recurring", frequency="fortnightly", start_date=(today + timedelta(days=4)).isoformat(), end_type="never", active=True),
        Cashflow(label="Rent", amount=1150, direction="expense", kind="recurring", frequency="monthly", start_date=(today + timedelta(days=7)).isoformat(), end_type="never", active=True),
        Cashflow(label="Groceries", amount=180, direction="expense", kind="recurring", frequency="weekly", start_date=(today + timedelta(days=2)).isoformat(), end_type="never", active=True),
        Cashflow(label="Insurance", amount=420, direction="expense", kind="one_off", start_date=(today + timedelta(days=18)).isoformat(), end_type="never", active=True),
    ])
    db.add_all([
        Holding(ticker="AAPL", shares=10, cost_per_share=150, currency="USD", opened_date=today.isoformat()),
        Holding(ticker="VAS.AX", shares=40, cost_per_share=92, currency="AUD", opened_date=today.isoformat()),
        Holding(ticker="ASML.AS", shares=2, cost_per_share=650, currency="EUR", opened_date=today.isoformat()),
    ])
    db.commit()

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo(db)
    def refresh_quotes_job():
        with SessionLocal() as db:
            portfolio_summary(db)
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(refresh_quotes_job, "interval", minutes=15, id="quote_refresh", replace_existing=True)
    scheduler.start()

@app.get("/api/auth/status")
def auth_status(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(os.getenv("SESSION_COOKIE_NAME", "cashflow_session"))
    authed = False
    if token:
        try:
            current_user(request, db); authed = True
        except HTTPException:
            authed = False
    return {"authenticated": authed, "has_passkey": has_credentials(db), "rp_id": os.getenv("WEBAUTHN_RP_ID", "cash.daviddekker.com")}

@app.post("/api/auth/register/options")
def register_options(payload: CredentialNameIn, db: Session = Depends(get_db), user=Depends(current_user)):
    return registration_options(db, payload.name)

@app.post("/api/auth/register/first/options")
def first_register_options(payload: CredentialNameIn, db: Session = Depends(get_db)):
    if has_credentials(db):
        raise HTTPException(403, "First-run registration is closed")
    return registration_options(db, payload.name)

@app.post("/api/auth/register/verify")
def register_verify(payload: dict, request: Request, response: Response, db: Session = Depends(get_db)):
    if has_credentials(db):
        current_user(request, db)
    return verify_registration(db, payload.get("credential", payload), payload.get("deviceName"), response)

@app.post("/api/auth/login/options")
def login_options(db: Session = Depends(get_db)):
    if not has_credentials(db):
        raise HTTPException(400, "Register a passkey first")
    return authentication_options(db)

@app.post("/api/auth/login/verify")
def login_verify(payload: dict, response: Response, db: Session = Depends(get_db)):
    return verify_authentication(db, payload.get("credential", payload), response)

@app.post("/api/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    clear_session(db, request, response)
    return {"ok": True}

@app.get("/api/cash/summary")
def cash_summary(db: Session = Depends(get_db), user=Depends(current_user)):
    anchors = db.query(Anchor).order_by(Anchor.date, Anchor.id).all()
    items = db.query(Cashflow).all()
    today = date.today()
    balance, anchor, occs = calculated_balance(anchors, items, today)
    fc = build_forecast(anchors, items, today, 60)
    return {"today": today.isoformat(), "balance": balance, "anchor": AnchorOut.model_validate(anchor).model_dump() if anchor else None, "today_transactions": [{"label": o.label, "amount": o.amount, "direction": o.direction} for o in occs if o.date == today], "forecast": fc}

@app.post("/api/cash/overwrite", response_model=AnchorOut)
def overwrite_balance(payload: OverwriteIn, db: Session = Depends(get_db), user=Depends(current_user)):
    anchor = Anchor(date=date.today().isoformat(), amount=payload.amount, note=payload.note)
    db.add(anchor); db.commit(); db.refresh(anchor)
    return anchor

@app.get("/api/anchors", response_model=list[AnchorOut])
def list_anchors(db: Session = Depends(get_db), user=Depends(current_user)):
    return db.query(Anchor).order_by(Anchor.date.desc(), Anchor.id.desc()).all()
@app.post("/api/anchors", response_model=AnchorOut)
def create_anchor(payload: AnchorIn, db: Session = Depends(get_db), user=Depends(current_user)):
    obj = Anchor(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj
@app.put("/api/anchors/{id}", response_model=AnchorOut)
def update_anchor(id: int, payload: AnchorIn, db: Session = Depends(get_db), user=Depends(current_user)):
    obj = db.get(Anchor, id) or (_ for _ in ()).throw(HTTPException(404));
    for k,v in payload.model_dump().items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj
@app.delete("/api/anchors/{id}")
def delete_anchor(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    obj = db.get(Anchor, id) or (_ for _ in ()).throw(HTTPException(404)); db.delete(obj); db.commit(); return {"ok": True}

@app.get("/api/cashflows", response_model=list[CashflowOut])
def list_cashflows(db: Session = Depends(get_db), user=Depends(current_user)):
    return db.query(Cashflow).order_by(Cashflow.active.desc(), Cashflow.start_date).all()
@app.post("/api/cashflows", response_model=CashflowOut)
def create_cashflow(payload: CashflowIn, db: Session = Depends(get_db), user=Depends(current_user)):
    obj = Cashflow(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj
@app.put("/api/cashflows/{id}", response_model=CashflowOut)
def update_cashflow(id: int, payload: CashflowIn, db: Session = Depends(get_db), user=Depends(current_user)):
    obj = db.get(Cashflow, id) or (_ for _ in ()).throw(HTTPException(404));
    for k,v in payload.model_dump().items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj
@app.patch("/api/cashflows/{id}/toggle", response_model=CashflowOut)
def toggle_cashflow(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    obj = db.get(Cashflow, id) or (_ for _ in ()).throw(HTTPException(404)); obj.active = not obj.active; db.commit(); db.refresh(obj); return obj
@app.delete("/api/cashflows/{id}")
def delete_cashflow(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    obj = db.get(Cashflow, id) or (_ for _ in ()).throw(HTTPException(404)); db.delete(obj); db.commit(); return {"ok": True}

@app.get("/api/holdings", response_model=list[HoldingOut])
def list_holdings(db: Session = Depends(get_db), user=Depends(current_user)):
    return db.query(Holding).order_by(Holding.ticker).all()
@app.post("/api/holdings", response_model=HoldingOut)
def create_holding(payload: HoldingIn, db: Session = Depends(get_db), user=Depends(current_user)):
    obj = Holding(**payload.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj
@app.put("/api/holdings/{id}", response_model=HoldingOut)
def update_holding(id: int, payload: HoldingIn, db: Session = Depends(get_db), user=Depends(current_user)):
    obj = db.get(Holding, id) or (_ for _ in ()).throw(HTTPException(404));
    for k,v in payload.model_dump().items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj
@app.delete("/api/holdings/{id}")
def delete_holding(id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    obj = db.get(Holding, id) or (_ for _ in ()).throw(HTTPException(404)); db.delete(obj); db.commit(); return {"ok": True}
@app.get("/api/portfolio")
def get_portfolio(refresh: bool = False, db: Session = Depends(get_db), user=Depends(current_user)):
    return portfolio_summary(db, force=refresh)

static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
