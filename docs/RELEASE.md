# Release checklist

## Before tagging

- [ ] `cd backend && ruff check . && pytest -q` — green
- [ ] `cd frontend && npm run lint && npm run typecheck && npm run test && npm run build` — green
- [ ] Review new Alembic revisions: `alembic history` — every `upgrade` has a matching `downgrade`
- [ ] Diff `backend/.env.example` and root `.env.example` against the last release; document any new required key in the README
- [ ] `NOTICE` updated if a dependency's license changed; `models/README.md` updated if `best.pt` changed (eval report, dataset DOI, training commit)

## Cut the release

- [ ] `git tag vX.Y.Z && git push --tags`
- [ ] CI `release` job builds and pushes `ghcr.io/<owner>/smart-qora-backend` and `-frontend` at that tag and attaches `LICENSE` + `NOTICE`

## Deploy to a box

- [ ] `docker compose exec db pg_dump -U postgres smart_qora > backup-$(date +%F).sql`
- [ ] `git pull && docker compose up -d --build` (runs `alembic upgrade head`)
- [ ] `curl -fsS localhost/api/ready` → `200`
- [ ] Sign in, confirm the live preview and a test crossing, check `/api/statistics/today`

## Rollback

- [ ] `git checkout <previous-tag> && docker compose up -d --build`
- [ ] If a migration ran: `docker compose exec backend alembic downgrade <previous-revision>`
- [ ] If the model was swapped: `cp models/best.prev.pt models/best.pt` then `POST /api/worker/restart`
