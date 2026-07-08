# Architecture Decision Records (ADRs)

Short records of significant, hard-to-reverse decisions and **why** they were made.
Read the relevant ADR before reversing a choice — the constraint that drove it
(e.g. cPanel can't run Chrome) usually still applies.

Format: [Michael Nygard's ADR style](https://github.com/joelparkerhenderson/architecture-decision-record).
Copy [`0000-template.md`](0000-template.md), number sequentially, keep it to a page.

| # | Decision | Status |
|---|----------|--------|
| [0001](0001-flask-over-fastapi.md) | Flask (not FastAPI) for the backend | Accepted |
| [0002](0002-mysql-over-sqlite.md) | cPanel MySQL (not SQLite) for storage | Accepted |
| [0003](0003-no-selenium-http-data-layer.md) | HTTP data layer, no Selenium | Accepted |
| [0004](0004-cookie-sessions-over-jwt.md) | httpOnly cookie sessions (not JWT) | Accepted |
| [0005](0005-fernet-per-user-encryption.md) | Fernet per-user encryption at rest | Accepted |
