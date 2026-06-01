# Personal Cashflow & Portfolio Dashboard

Self-hosted, single-user dashboard for:

- the calculated AUD cash balance as of today;
- a 60-day cashflow forecast with peak/trough callouts;
- an AUD-normalised investment portfolio view for AUD, USD, and EUR holdings.

The stack is FastAPI + SQLite + React/Vite. FastAPI serves the built PWA so a single Docker Compose service is enough for production.

## Key security assumptions

- The application is for one owner only. There is no public signup.
- First run registers the owner's passkey. After that, registration is closed unless you are already authenticated and add another device.
- WebAuthn is configured for `cash.daviddekker.com`; the app must be reached via HTTPS at that host.
- Sessions use a secure, httpOnly, SameSite cookie. Every data API endpoint rejects unauthenticated calls.
- Cloudflare Access or another outer layer is optional defence-in-depth, not a replacement for passkeys.

## Quick start

```bash
cp .env.example .env
# edit .env if needed; leave WEBAUTHN_RP_ID and WEBAUTHN_ORIGIN as cash.daviddekker.com for production
docker compose up -d --build
```

The SQLite database is stored in the `cashflow_data` Docker volume at `/data/cashflow.db` inside the container.

### Demo data

Set `SEED_DEMO=true` in `.env` before first startup to insert sample anchors, cashflows, and holdings. Set it to `false` for a clean database. Seeding only runs if there are no anchors yet.

## SWAG reverse proxy

Copy `deploy/cash.subdomain.conf` to your SWAG nginx proxy-confs folder and ensure the `cashflow` container is on the same external Docker network as SWAG (the compose file expects a network named `swag`). The important lines for passkeys are:

```nginx
proxy_set_header Host $host;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Forwarded-Proto https;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $connection_upgrade;
```

The original `Host` must stay `cash.daviddekker.com`, otherwise the WebAuthn RP ID check will fail.

## First-run passkey registration

1. Browse to `https://cash.daviddekker.com` on your iPhone or desktop.
2. If the database has no passkeys, the unlock screen shows **First run: register your passkey**.
3. Name the device and tap **Create owner passkey**.
4. Complete the platform passkey prompt.
5. Future visits use **Sign in with passkey**.

To register additional devices, sign in first, then use the same registration endpoint from a trusted browser session. No password fallback is provided by design.

### iPhone PWA install

1. Open `https://cash.daviddekker.com` in iOS Safari.
2. Sign in once with your passkey.
3. Tap Share → **Add to Home Screen**.
4. Launch **Cashflow** from the home screen. The manifest uses `display: standalone`, and the service worker caches shell assets for an app-like full-screen experience.

Modern iOS Safari and standalone PWAs support passkeys for the same origin. If a passkey prompt fails, confirm HTTPS is valid, the URL host is exactly `cash.daviddekker.com`, and SWAG preserves the `Host` header.

## Cashflow model

The displayed cash balance is never raw bank data. It is calculated from anchors plus projected cashflow occurrences:

```text
Calculated balance on date D = amount of the most recent anchor with date <= D
+ net sum (income - expense) of every cashflow occurrence strictly after that anchor date and on or before D.
```

This means an overwrite is just a new anchor. If today has an unexpected transaction, tap **Overwrite balance as of today**, enter the real balance, and the graph immediately re-bases from the new anchor without double-counting older projected transactions.

Recurring items support:

- weekly;
- fortnightly;
- monthly;
- quarterly;
- annually.

End conditions support:

- never;
- stop on/before an end date;
- stop after N occurrences.

Monthly, quarterly, and annual recurrences preserve the original day-of-month where possible and clamp to the last day of shorter months (for example, a 31 January monthly payment occurs on 28 February in a non-leap year).

## Portfolio

Add holdings with:

- full yfinance ticker (`VAS.AX`, `AAPL`, `ASML.AS`, `SAP.DE`, `MC.PA`, etc.);
- shares;
- average cost per share;
- holding currency (`AUD`, `USD`, or `EUR`).

Quotes are fetched with `yfinance`, cached in SQLite, and refreshed on demand or by the 15-minute background schedule. FX rates are also fetched with yfinance and cached:

- `AUDUSD=X` is inverted for USD → AUD;
- `EURAUD=X` is used directly for EUR → AUD.

If markets are closed or yfinance fails, the app keeps and displays the most recent cached quote with its timestamp. Portfolio totals, allocation, and unrealised P/L are shown in AUD; native currency values are shown alongside each holding.

## Development

Backend:

```bash
cd backend
DATABASE_URL=sqlite:///./dev.db SEED_DEMO=true uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Tests:

```bash
cd backend
PYTHONPATH=. pytest
```

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:////data/cashflow.db` | SQLite database path. |
| `WEBAUTHN_RP_ID` | `cash.daviddekker.com` | WebAuthn relying party ID. |
| `WEBAUTHN_ORIGIN` | `https://cash.daviddekker.com` | Expected browser origin for passkey verification. |
| `WEBAUTHN_RP_NAME` | `Cashflow Dashboard` | Name shown in passkey prompts. |
| `OWNER_NAME` | `David` | Single-user display name. |
| `SESSION_DAYS` | `14` | Session cookie lifetime. |
| `SEED_DEMO` | `false` | Insert demo data on an empty database. |
