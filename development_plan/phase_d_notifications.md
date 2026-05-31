# Phase D: Notifications

**Status:** Deferred — planned for a future iteration

---

## Intended Outcome (User Perspective)

The user can opt in to receive push notifications on their device so they never miss a rare astronomical event or a good planet observation window:

- **Event notifications**: The user gets a push notification when a conjunction, opposition, Mercury elongation maximum, planet alignment, Venus at peak brilliance, or Moon occultation is happening within the next few hours — even when the app is closed.
- **"Tonight's highlights" daily summary**: Each evening (around sunset) the user receives a brief summary for their saved location: which planets are visible tonight, the best viewing window, and any notable events in the next 24 hours.

Notifications are opt-in, respect the user's notification settings, and link back to the relevant view in the app (e.g. the Kommande tab for an upcoming event, or the planet card for a visibility window).

---

## Definition of Done

- [ ] The user can enable or disable push notifications from the settings modal; the toggle is persistent across sessions
- [ ] A service worker is registered for the app that handles incoming push messages and displays a native OS notification with the correct title and body
- [ ] Event notifications are triggered for each of the six event types in `events.py` when an event is within a configurable lead time (default: 6 hours before the event)
- [ ] The "tonight's highlights" summary notification is sent once per evening per saved location, within 30 minutes of local sunset
- [ ] Tapping a notification on mobile or clicking it on desktop opens the app and navigates to the relevant tab (Kommande for events, Planeter for highlights)
- [ ] Notifications are not sent when the user has already viewed the event in the app within the notification lead-time window (deduplication)
- [ ] The backend supports a notification subscription endpoint (`POST /api/v1/notifications/subscribe`) that stores the user's push endpoint and keys
- [ ] Notification content is entirely in Swedish
- [ ] Notification delivery degrades gracefully: if push delivery fails for a given subscriber, the failure is logged and does not affect other subscribers or any other app functionality

---

## Dependencies

- Phase 5 (API Layer)
- Phase B4 (Astronomical Event Alerts) — for event detection logic
- Phase B5 (Kommande Events Timeline) — for event data source

---

## Notes

- Requires selecting a push notification backend (e.g. Web Push Protocol with VAPID keys; self-hosted or via a third-party service).
- The browser's Push API requires HTTPS; ensure the deployment environment provides a valid TLS certificate.
- A backend scheduler (e.g. APScheduler or a cron job) is needed for the nightly summary delivery.
- Privacy: push subscription endpoints should not be stored alongside personally identifiable information.
