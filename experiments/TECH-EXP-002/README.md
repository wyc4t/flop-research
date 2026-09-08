# TECH-EXP-002: signed replies contradicted explicit probe instructions

One four-probe block in Technocore's credence room on 2026-09-08 produced six attributable replies within 120-second windows. Five were prohibited ACCEPT/SUBMIT messages; one was an ACK to a plain-text message saying not to reply. Neither ACK-requesting probe received the requested ACK.

| Condition | Surface / instruction | Replies | First latency |
|---|---|---:|---:|
| B | TASK / no reply | 2 ACCEPTs | 17.191281 s |
| C | Plain / exact ACK | 0 | — |
| A | TASK / exact ACK | 2 ACCEPTs + 1 SUBMIT | 24.145100 s |
| D | Plain / no reply | 1 ACK | 57.615752 s |

This supports specific instruction mismatches. One sequential block cannot establish a causal surface-trigger mechanism, response rates, agent exposure, or operator independence. Claimed work was not independently verified.

Read [the full report](original-evidence/REPORT.md), [provenance and scoring amendments](PROVENANCE.md), and [exact reviewed outcomes](outcomes-reviewed.json). The original report and evidence remain intact in original-evidence. Current runner source and earlier attempt records supplement them.

## Verify offline

With Python and cryptography installed, run from this directory:

```bash
python3 original-evidence/verify_evidence.py
```

This checks the original evidence package, not behavioral replication. SHA256.json at this directory's root fingerprints the additional publication files. Signatures authenticate payloads, not venue times.

## Useful builder follow-up

Replay the archived probes through your own local decision logic with controlled exposure. Check that no-reply messages produce no action, and that an engaged response to an exact-ACK request produces only that ACK. Test isolated messages and then the recorded order to examine contextual carryover. These are proposed regression cases, not a diagnosis of a particular agent.
