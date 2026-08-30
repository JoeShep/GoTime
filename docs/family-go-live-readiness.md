# Family go-live readiness audit — 2026-08-29

This audit is read-only and does not authorize deployment.

| Boundary | Current state | Smallest viable next step |
| --- | --- | --- |
| Private family access | Compose publishes the app on all host interfaces; no private-access layer is configured in this repository. | Put the app behind an authenticated private tunnel/VPN, or bind it to loopback and use an authenticated reverse proxy. |
| Protected transport | Local HTTP only; repository Compose has no TLS termination. | Terminate HTTPS in the chosen private tunnel or reverse proxy. |
| Authentication | Normal Plan/Now APIs and UI have no authentication middleware. | Require identity at the proxy/tunnel boundary before any non-local exposure. |
| Mobile access | The responsive UI supports narrow screens, but safe off-host reachability is not established. | Validate the chosen protected endpoint on the family phones after the access boundary exists. |
| Backups | Durable, checksummed pre-change backups exist, but no scheduled backup frequency is configured by the application. | Schedule encrypted daily SQLite snapshots and retain multiple generations. |
| Restore | Exact byte-for-byte Docker-volume restore has been rehearsed and durable evidence retained. | Keep rehearsing after material schema/data changes. |
| Data export | No user-facing downloadable complete-plan export exists. | Add a deterministic JSON/CSV export before treating GoTime as the only family record. |
| Failed saves/connections | Editors retain drafts and show bounded request errors; there is no offline write queue. | Human-test network loss on phones and keep another communication channel for urgent changes. |
| Container operations | Backend has a healthcheck; normal containers currently have zero restarts. Compose does not declare a restart policy. Frontend has no healthcheck. | Add explicit restart policies and a frontend healthcheck in a separately reviewed operations change. |
| Runtime dependencies | Normal family planning is deterministic. Both experiment flags are false; no API key, AI call, research call, or external service is required. | Keep experiment routes disabled and avoid adding runtime AI to family go-live. |

Safe family access is not yet established by repository configuration. Do not
expose the current HTTP ports beyond a trusted local machine until the user
chooses a protected access boundary.
