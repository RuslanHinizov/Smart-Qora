# Counting reliability corrections — 2026-09-07

## Scope and implementation order

1. Replace lifetime track-ID uniqueness with session-scoped event uniqueness. Keep legacy events intact.
2. Count each file once per camera, identified by SHA-256 of its contents. Persist completed playback and a processed-frame watermark in the same transaction as each crossing, plus periodic checkpoints. Reconstruct tracker state by replaying the prefix after interruption; do not save crossings from that prefix. Preview loops never save events, regardless of assigned track IDs.
3. Use the site's `TZ` (default Asia/Almaty) for daily rollups, API dates and Telegram. Rebuild derived daily rollups from unchanged event timestamps. Live statistics carry today's totals; current occupancy remains independent and calibratable.
4. Keep filtered/paginated event results server-authoritative. Batch cache invalidations during event bursts and refresh on reconnect. Refresh daily totals even with no crossings.
5. Make one active counting camera explicit. Enforce it in the database, switch the worker on camera changes, honor inactive state, preserve masked passwords on edits, and prohibit deleting cameras with counting history.
6. Apply persisted detection defaults; distinguish explicit zero from inheritance. Validate complete/nondegenerate counting lines and usable dual gates before accepting settings. Preserve delayed dual-gate crossings until minimum track age is reached.
7. Add regression tests, run backend/frontend checks, validate migrations on PostgreSQL, back up the current database and update the local installation.
8. Move browser stream/WebSocket authentication from URL query parameters to an HttpOnly session cookie and clear it on logout.

## Operating semantics

- This deployment counts one active camera at a time; the Cameras page is a source selector, not a simultaneous multi-camera engine.
- A completed recording is preview-only on replay, worker restart and camera reactivation. A renamed copy with identical contents is still the same recording. A changed file has a new identity. Use the offline evaluation script to compare settings/models without changing barn occupancy.
- Live feeds receive a fresh session identity on worker restart, so reused track IDs no longer collide with historical animals. This does not identify individual animals across downtime; camera outages and tracker fragmentation can still affect physical counting accuracy.
- An interrupted file replays its prefix to reconstruct tracker state. A hard crash inside a frame still relies on session-scoped event deduplication for any partially committed frame; GPU inference is not an exactly-once physical identity guarantee.
- Existing pre-migration footage has no source/session provenance. During this installation's upgrade, explicitly register the already-counted active demo recording as completed to preserve its 39 existing records. Do not infer this association for other deployments.
- Changing `TZ` later requires rebuilding derived daily rollups. Event timestamps remain UTC.
- Downgrading to the old unique constraint is refused when it would collapse multiple sessions; restore the backup instead of deleting history.

## Model accuracy remains separate

The historical 158/158 measurement reuses the training dataset's clips. It is not independent field accuracy. The reported `id_switch_ratio` was a track-count ratio, not an identity-switch measurement. New reports name it `track_count_ratio` and sum absolute IN/OUT errors per clip, so errors cannot cancel across clips or directions.

The earlier 43-animal video comparison (47 with the shipped model, 49 with the candidate) is historical evidence, not a rerun in this change. No checkpoint is replaced and no perfect model accuracy is claimed. Manual corrected labels and a separate unseen-video evaluation are still required.
