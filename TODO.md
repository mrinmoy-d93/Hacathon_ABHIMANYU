# KHOJO — Phase 7 follow-ups

Tracking deferred items from the FRS that couldn't be satisfied cleanly with
current dependencies in Phase 5.

## UI

- **User search for "Add Field Worker"**
  FRS §6.6 Tab 3 calls for a user picker when assigning a new field worker.
  The Phase 4 backend only exposes `POST /admin/field-workers` with a
  `user_id`. Current UI falls back to a raw UUID input.
  _Fix in Phase 7:_ add `GET /admin/users?role=field_worker_candidate&q=…`
  on the backend and an async combobox (shadcn `Command`) on the frontend.

- **My-cases list for family users**
  The community-member landing (`/cases`) currently only deep-links to the
  new-case flow; there's no "list of my cases" because the backend lacks
  `GET /cases?owner=me`. Users can still open a case by pasting the
  `KHJ-YYYY-XXXXX` reference.
  _Fix in Phase 7:_ add the endpoint + a paginated list view.

- **Geo-heatmap on Admin Overview**
  FRS §6.6 Tab 1 mentions a state-level sighting heatmap. Not implemented
  yet — requires geocoded sighting data in the admin dashboard payload.
  _Fix in Phase 7:_ extend `AdminDashboard` with a `heatmap: {lat,lng,count}[]`
  field and integrate a lightweight map (e.g. Leaflet).

- **Live leave-status column**
  `FieldWorkerRow` doesn't include `leave_status` today, so the table's
  leave column would show "—" for everyone. Edit modal still allows toggling
  leave, but the table read path needs the field.
  _Fix in Phase 7:_ add `leave_status` to the row schema.

- **Geo-clustering radius and min-count sliders**
  FRS §6.6 Tab 4 lists both as tunable. Not surfaced in the current AI
  Settings page because they're absent from `SettingsUpdate`.
  _Fix in Phase 7:_ extend the settings schema and add two numeric inputs.

- **shadcn/ui via CLI**
  Primitives are hand-rolled in `components/ui/*` using the standard shadcn
  sources. They compile and behave correctly but weren't scaffolded through
  `npx shadcn-ui` — the CLI's interactive prompts don't fit a non-TTY
  environment. Functionally identical; if upstream shadcn changes a
  component's API, run the CLI locally to regenerate.

## Polish

- **Screenshots in `docs/SCREEN_INVENTORY.md`** — currently placeholders.
- **Internationalisation** — only English today. FRS §14 targets Hindi,
  Gujarati, Marathi, Tamil, Bengali, Telugu.
- **SMS-provider integration for demo OTP** — wired to the `/send-otp`
  endpoint which currently just logs in demo mode. Replace with Twilio /
  MSG91 for production before going live.
