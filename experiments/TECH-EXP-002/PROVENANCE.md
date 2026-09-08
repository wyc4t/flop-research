# Provenance and review amendments

Prepared 2026-09-08. This supplement leaves original-evidence unchanged.

The original review found approval and earlier attempts absent from the supplied ZIP. Subsequent workspace inspection found local approval records, source and attempt logs, now included here. This corrects any impression that those records were absent from the project.

The v1.3 USER-APPROVAL.json records approval at 2026-09-08T12:54:11.893713+00:00 for plan dad6cd5c222a91eff9639edbea9c20ef8b3f73a4f499546220847faa4496ab8c, before the first probe at 13:20:02.544308 UTC. It describes a user yes after the exact messages, offsets and hash were displayed. This is a local approval record, not an independently timestamped receipt or a verbatim export of the approval conversation. The frozen plan's AWAITING_NEW_APPROVAL label is retained to preserve its hash.

v1 was excluded after the per-probe gating flaw; v1.1 was interrupted after manual timing failed. The v1.3 plan identifies v1.2 as interrupted after B/C and excludes it. Included v1.2 attempt logs provide additional history. Three v1.3 NO-GO summaries record zero post attempts at 12:55:53.814252, 12:57:49.782970 and 13:02:20.341555 UTC. Attempt 004 completed.

The historical minimum 60-second cooldown became absolute target dispatch offsets in v1.3. A to D's venue cooldown was 59.980733 seconds, 19.267 ms below the old strict minimum, consistent with the v1.3 target schedule. Inclusive zero-latency attribution in v1.3 also differs from the original strict positive-latency rule; no observed response lies at that boundary.

The historical rubric scored C silence as non-compliant. The supplement records requested output absent, without assigning an unseen participant a comprehension failure. Semantic compliance is separate from an ACK-shaped string match.

runner-source contains copies of the current local v1.3 implementation for inspection. No contemporaneous pre-run source hash has been established; these copies are not proven to be the exact executed bytes. The runner references a local Technocore client dependency that is not bundled and contains a machine-specific path. It is not a portable live-run distribution. Use the standalone offline verifier in original-evidence for archive verification.

Payload signatures do not authenticate venue timestamps, sequence numbers, local approval time, or independence of operators. Package hashes demonstrate internal consistency only.
