# Findings ledger — 8 November 2026

## Supported observations

| Finding | Scope | Evidence |
| --- | --- | --- |
| Signed replies can contradict explicit instructions | Six attributable replies in one completed Credence block; mechanism and exposure unknown | [TECH-EXP-002](../experiments/TECH-EXP-002/README.md) |
| Complete-looking records are not proof of useful work | Signature validity, stage relationships and semantic fulfillment are distinct | [Proofline evidence model](https://github.com/wyc4t/proofline-technocore) |
| Evidence can survive an empty live export | Original preserved Credence bundle reproduced; dated captures bracket the nonempty/empty transition | [Preservation finding](https://github.com/wyc4t/proofline-technocore/tree/main/findings/2026-10-24-credence-preserved) |
| PaperRail exact verification omits terms at the audited main revision | Source inspection at `7d402db451ad952e3695e8ce9a8fcac99893950b`; amount, asset, payer, payee and claim deadline omitted | [Pinned source](https://github.com/flop-labs/tclk/blob/7d402db451ad952e3695e8ce9a8fcac99893950b/src/paper-rail.ts), [proposed fix #122](https://github.com/flop-labs/tclk/pull/122) |
| Preserved signed handshakes permit bounded offline replay | Tested fixture/negative controls; does not create durable public storage or prove money moved | [Published replay observation](https://github.com/flop-labs/tclk/issues/181#issuecomment-6146691745) |
| Rehearsal lifecycle state should not establish money outcomes | Local integration/guard tests; proposal not confirmed adopted | [#173 guard](https://github.com/flop-labs/tclk/pull/173#issuecomment-6384788362) |
| Onboarding may succeed despite a lost client response | One sponsor attempt ended fetch-failed; subsequent registration/calibration observed. Attribution to that attempt is an inference | [Operator postmortem](../reports/2026-11-08-devnet-miner/README.md) |
| Client failure can follow successful settlement | One self-test paid and closed, independently reconciled; original reply/full receipt not retained | [Settlement summary](../reports/2026-11-08-devnet-miner/evidence/self-test-settlement.json) |
| Retirement succeeded before host destruction | Finalized extrinsic, registration absent, sponsor unbonding event; provider destruction separately user-reported | [Independent RPC record](../reports/2026-11-08-devnet-miner/evidence/retirement-independent-verification.json) |

## Explicit corrections and invalidated methodology

- **Incorrect:** PaperRail was already fixed on main at fb910d3. Source at that commit and audited main 7d402db still omits the five terms; #122 remained open/unmerged at the audit.
- **Invalid controlled block:** earlier manually timed Credence pilots could not sustain the schedule. Keep them as pilot/provenance evidence, outside the final block.
- **Incorrect inference:** a client's fetch/settlement error proves rejection or no payment. Reconcile the authoritative state before retrying.
- **Unsupported:** paid self-test answered correctly. Its wrapper saved the reply only after overall success; the later exception prevented retention. A separate correct local diagnostic does not recover it.
- **Unsupported:** September Yellow Paper reproducers passed. That baseline was static inspection only.
- **Superseded:** the driver mismatch was still unresolved after the authorized14:06 UTC repair; all later Proofline work remained draft; the replacement maintainer room remained unclaimed.
- **Unsupported:** a pause stops all rental charges. Provider storage is billed separately; the user's destruction report is not an independently inspected final bill.
- **Invalid controls corrected in earlier peer review:** unconnected socket creation did not test outgoing access; a nonexistent-file denial did not test the intended existing-file restriction. Corrected controls, not those initial attempts, support the isolation observation.

## Open questions

1. What deployed scoring-network/release path creates eligible verified-work credit, distinct from payment-only channels?
2. What explains the direct client's close-confirmation failure? A race/timeout is a hypothesis, not an established root cause.
3. What durable proof/transcript retention is required and demonstrably configured for a future miner?
4. Can unfamiliar human readers find, inspect, understand and cite a Proofline case without help? The prepared five-reader study has no completed participants in the retained results.
5. Is there repeat use or independent demand? Other wallet addresses, external reviews and raw traffic do not answer this alone.
6. Have upstream authors adopted the submitted integration/recovery/test patches? PR state, code adoption and release status need separate checks.
7. Are any separately billed storage resources or final provider charges left? No provider billing inspection followed the user's destruction report.
8. What were final contest eligibility, prize, payout and X-publication outcomes? The recovered evidence does not settle them.

## Possible next tests

Prioritize one: complete Proofline maintainer integration; run the human reader study; reproduce source-level cache invalidation concerns with controlled record changes; independently rerun the public Yellow Paper checks at a current pinned revision; or identify the actual testnet credit path before another rental. Publication, paid tests, signed messages and new resources require their own authorization.
