# Devnet miner rehearsal: settlement, recovery and retirement

Recorded through 8 November 2026. This is a sanitized operator postmortem with selected public receipts. Private recovery/configuration, keys, endpoint access and provider account details are excluded.

## Objective

Establish whether one existing miner identity could complete onboarding, accepted calibration and one bounded direct session, then preserve recovery material and retire without leaving active work. The direct test hypothesized a correct answer plus a verifiable receipt and reconciled settlement; not all of those outcomes were demonstrated.

## Setup and timeline

- Existing miner: `5HpDEPBhnxZmDmMBpWHSwE1LtvYaufUfKZZBgPnnfgBPr8d3`. The direct self-test caller was controlled by the same operator; it is not independent demand.
- Devnet genesis: `0x99c172c095340ace980631f9123544c6bebd4839f3437e463533422d8be2d631`; runtime 1014014; 18 decimals.
- Working pins: CLI 0.1.290, worker 0.1.286, backend 0.1.239; RTX 4090; Qwen2.5-0.5B-Instruct BF16, measured model root recorded in evidence.
- A one-shot sponsor request ended with a client fetch error; later public chain reads established registration at block 3216918 and 1,000,000 active sponsored test FLOP. Attribution to that request is an inference, not a recovered server response.
- Accepted Soft calibration at block 3218214: 64 verified jobs over 626 blocks, cap 130, version 1. The cap is protocol calibration, not a physical GPU benchmark or TEE attestation.
- One approved direct self-test opened and settled cooperatively on 8 Nov. No automatic retry after the client error.
- An unattended driver update produced a loaded-module/library mismatch. A later authorized module reload restored driver 580.178.04, fresh container GPU access, measured backend health and local inference without rebooting the VM. That diagnostic was separate from the paid test.
- After evidence/recovery checks, the miner retired successfully at block 3226868. Services were stopped. The operator subsequently reported destroying the provider instance; final account billing and separate storage were not independently inspected.

## Direct session: payment succeeded, reply not retained

Exact prompt: `What is 2 + 2? Answer with just the number.` Maximum 16 completion tokens; escrow 0.01 devnet FLOP.

The worker acknowledged the turn and cooperatively settled. Direct RPC independently confirmed the exact `computeChannel.settle` extrinsic and successful finalized events at block 3219349, with miner payment 0.0099 and audit earmark 0.0001. Caller balance decrease 0.017391811525 consisted of escrow plus opening fee. No caller escrow recovery was needed.

The client then reported `cannot settle without a finalized Open channel`. Finalized state was already Closed. A confirmation race/timeout is plausible, but the underlying cooperative-close exception was not preserved, so no root cause is established.

The wrapper persisted reply/receipts only after the high-level session returned successfully. That methodology lost the answer/full receipt when a later step threw. Consequently **answer correctness and independent receipt/TOPLOC replay are not established**. A later local diagnostic produced correct arithmetic but exceeded the requested answer format; it does not recover the earlier answer.

[Selected settlement fields](evidence/self-test-settlement.json) are copied from a retained indexed response, with prior direct-RPC reconciliation explicitly labeled. The indexer's original selfTrade flag is not used for ownership classification. Copying a receipt summary is not a fresh re-execution.

## Retirement

User approved interruption, private backup and one retirement transaction with an estimated fee ceiling of 2 devnet FLOP. Before pausing worker, finalized busy/session reservations were zero. A single-use guard rechecked both current/finalized counters after worker exit, required the exact genesis/runtime/account, checked the fee estimate, and wrote an exclusive submission marker. It used the already available pinned CLI image, not a floating release.

Fresh private recovery material was checked on the host and local machine by checksum and archive-directory coverage. Its contents and location are deliberately not included here. That is backup integrity/coverage, not a full restored-host qualification.

One transaction `0x23545984aac880a24a809c82b0bb036102237cb820d1442edf33501f268070a0` finalized at block 3226868. Separate read-only RPC inspection at 15:52:54.309 UTC verified exact extrinsic hash/call, successful dispatch, `MinerDeregistered` and registration absent at that block. `SponsorUnbondingStarted` names position 232 and unlock block 3831668. Sponsored principal belongs to its sponsor and remains subject to its unbonding/slashing rules until withdrawal.

Estimated fee 1.58987469054 test FLOP; actual `TransactionFeePaid` **0.04564075054 test FLOP**. No real funds or new rental credit were used by retirement. At 15:53:27.656586 UTC worker/backend were exited and tunnel inactive; the VM was still running then. The later destruction is **operator-reported**, not an independently verified provider event.

[Independent chain verification](evidence/retirement-independent-verification.json) and [raw public event receipt](evidence/retirement-result.json) are retained. [SHA-256 manifest](evidence/SHA256.json) records exact included bytes.

## How the chain checks were performed

Read-only Polkadot API 17.0.2 against `wss://rpc.devnet.flop.network`, independently of the signing process. Exact retirement block hash:

`0x3127c016e1dec717582b6f7aa318f9d52fa5ec9c71336a0992f6a4f1707fb2a9`

The verifier called `chain.getBlock(blockHash)`, located the extrinsic by its exact transaction hash, read `system.events` and `minerStaking.miners(miner)` through `api.at(blockHash)`, and selected events whose ApplyExtrinsic index matched2. It required the expected call, ExtrinsicSuccess, MinerDeregistered and absent registration. It read the actual fee from TransactionFeePaid, not the unsigned estimate. The adjacent JSON preserves output and public bindings. This is a method/receipt record, not a packaged installation or a replay of model execution.

## Lessons and limits

1. Reconcile chain state after ambiguous client errors before retrying; a client error can follow a successful state change.
2. Persist deliverables/receipts before a final confirmation can fail.
3. Calibration, channel payment, task quality, work credit and economic return are separate claims.
4. Hardware rental requires recovery and exit planning. Pausing provider compute may retain billable storage; stopping application services alone does not stop provider billing.
5. Distinct caller addresses do not prove independent customers. Later indexed requests existed, but no customer census or profit claim is made.

No real-world revenue, airdrop allocation, entire-network reliability or confidential execution was demonstrated. Missing durable transcript evidence and the SDK confirmation failure remain open. Devnet rehearsal is useful preparation; official documentation says devnet earns no airdrop weight. See [official timeline](https://docs.flop.network/docs/testnet-and-timeline), [conversion/status guide](https://docs.flop.network/docs/airdrop-and-testnet-conversion), and [Vast billing rules](https://github.com/vast-ai/docs/blob/main/guides/reference/faq/billing.mdx). These sources describe their own stated policies and may change; this report records the dated experiment.
