# Security and deployment checklist

## Security controls in this MVP

- Secrets are loaded from environment variables; `.env` is ignored by Git and excluded from Docker build context.
- The public API never returns exception tracebacks. Validation errors omit submitted input values.
- Uploaded document names are sanitized, file extensions and size are allow-listed, and stored paths are verified before deletion.
- Document checksums block duplicate content per Agent. ChromaDB collections and document queries are scoped by Agent ID.
- Retrieved document text is treated as untrusted data and is separated from Agent/Persona system instructions.
- Browser responses use content-type, frame, referrer, permissions, and CSP protections. API docs are exempted from the CSP because Swagger loads its own assets.

## Before deploying

1. Set `APP_ENV=production`, `DEBUG=false`, a production `DATABASE_URL`, and a secure `OPENAI_API_KEY` through the platform secret manager.
2. Use PostgreSQL and managed persistent storage for production; SQLite is intended for local MVP use.
3. Place the service behind HTTPS with a reverse proxy and restrict network access to intended users.
4. Add authentication, authorization, tenant/organization boundaries, migrations, backups, monitoring, and rate limiting before exposing it to untrusted users.
5. Review uploaded-document retention and delete data according to your organization’s policy.

## Container deployment

Copy `.env.example` to `.env`, set production values, then run:

```bash
docker compose up --build -d
```

Check `http://localhost:8000/api/health` after deployment. The Compose volume persists SQLite, documents, and ChromaDB data across container recreation.
