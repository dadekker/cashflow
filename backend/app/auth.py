import hashlib, os, secrets, json, base64
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from webauthn import generate_registration_options, verify_registration_response, generate_authentication_options, verify_authentication_response, options_to_json
from webauthn.helpers.structs import PublicKeyCredentialDescriptor, UserVerificationRequirement, AuthenticatorSelectionCriteria
from .database import get_db
from .models import AuthChallenge, Session as UserSession, WebAuthnCredential

RP_ID = os.getenv("WEBAUTHN_RP_ID", "cash.daviddekker.com")
RP_NAME = os.getenv("WEBAUTHN_RP_NAME", "Cashflow Dashboard")
ORIGIN = os.getenv("WEBAUTHN_ORIGIN", f"https://{RP_ID}")
SESSION_COOKIE = os.getenv("SESSION_COOKIE_NAME", "cashflow_session")
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "14"))
OWNER_ID = b"single-owner"
OWNER_NAME = os.getenv("OWNER_NAME", "David")

def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def b64url_to_bytes(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def create_session(db: Session, response: Response):
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(days=SESSION_DAYS)
    db.add(UserSession(token_hash=token_hash(token), expires_at=expires))
    db.commit()
    response.set_cookie(SESSION_COOKIE, token, httponly=True, secure=True, samesite="lax", expires=expires, path="/")

def clear_session(db: Session, request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        row = db.get(UserSession, token_hash(token))
        if row:
            db.delete(row); db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")

def current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(401, "Authentication required")
    row = db.get(UserSession, token_hash(token))
    if not row or row.expires_at < datetime.utcnow():
        raise HTTPException(401, "Session expired")
    return {"name": OWNER_NAME}

def has_credentials(db: Session) -> bool:
    return db.query(WebAuthnCredential).count() > 0

def registration_options(db: Session, device_name: str | None = None):
    exclude = [PublicKeyCredentialDescriptor(id=b64url_to_bytes(c.id)) for c in db.query(WebAuthnCredential).all()]
    opts = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=OWNER_ID,
        user_name=OWNER_NAME,
        user_display_name=OWNER_NAME,
        exclude_credentials=exclude,
        authenticator_selection=AuthenticatorSelectionCriteria(user_verification=UserVerificationRequirement.REQUIRED),
    )
    db.add(AuthChallenge(kind="registration", challenge=opts.challenge.decode("utf-8") if isinstance(opts.challenge, bytes) else opts.challenge))
    db.commit()
    payload = json.loads(options_to_json(opts))
    payload["deviceName"] = device_name
    return payload

def verify_registration(db: Session, credential: dict, device_name: str | None, response: Response):
    challenge = db.query(AuthChallenge).filter_by(kind="registration").order_by(AuthChallenge.id.desc()).first()
    if not challenge:
        raise HTTPException(400, "No registration challenge")
    verification = verify_registration_response(
        credential=credential,
        expected_challenge=challenge.challenge,
        expected_origin=ORIGIN,
        expected_rp_id=RP_ID,
        require_user_verification=True,
    )
    db.merge(WebAuthnCredential(
        id=b64url(verification.credential_id),
        public_key=verification.credential_public_key,
        sign_count=verification.sign_count,
        name=device_name,
    ))
    db.delete(challenge); db.commit()
    create_session(db, response)
    return {"ok": True}

def authentication_options(db: Session):
    creds = [PublicKeyCredentialDescriptor(id=b64url_to_bytes(c.id)) for c in db.query(WebAuthnCredential).all()]
    opts = generate_authentication_options(rp_id=RP_ID, allow_credentials=creds, user_verification=UserVerificationRequirement.REQUIRED)
    db.add(AuthChallenge(kind="authentication", challenge=opts.challenge.decode("utf-8") if isinstance(opts.challenge, bytes) else opts.challenge))
    db.commit()
    return json.loads(options_to_json(opts))

def verify_authentication(db: Session, credential: dict, response: Response):
    challenge = db.query(AuthChallenge).filter_by(kind="authentication").order_by(AuthChallenge.id.desc()).first()
    if not challenge:
        raise HTTPException(400, "No authentication challenge")
    cred_id = credential.get("id")
    stored = db.get(WebAuthnCredential, cred_id)
    if not stored:
        raise HTTPException(401, "Unknown passkey")
    verification = verify_authentication_response(
        credential=credential,
        expected_challenge=challenge.challenge,
        expected_origin=ORIGIN,
        expected_rp_id=RP_ID,
        credential_public_key=stored.public_key,
        credential_current_sign_count=stored.sign_count,
        require_user_verification=True,
    )
    stored.sign_count = verification.new_sign_count
    stored.last_used_at = datetime.utcnow()
    db.delete(challenge); db.commit()
    create_session(db, response)
    return {"ok": True}
