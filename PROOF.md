# SkillBond — live proof record

Everything below was executed on chain and can be checked on the Bradbury
explorer (https://scan.bradbury.genlayer.com). Amounts are wei unless a GEN
figure is named (1 GEN = 1,000,000,000,000,000,000 wei).

## Deployments

| Deployment | Address | Deploy tx |
|---|---|---|
| Production | `0x067E9E2c911EB41F2A37B7D21333222d8df8c1e3` | `0xa99d6929d081d84444e1e61210c0a98a4c10001116e669d057c96206cb4b052f` |
| Proof twin (fast clock) | `0x1aAc6A349341F30D81361FaF8ed0372339324D44` | `0x6592ce46bda4a76836487851e25a3b843b93a4e787f5948a8f0189c09c83821a` |

Both deploys finalized with MAJORITY_AGREE / FINISHED_WITH_RETURN. The
production source is `SkillBond.py` in this repo, sha256
`1b650c61ce46e90f07bbf77a8494cf59177edc2b9b2d087f121c8e48f707081c`. The
twin runs the same logic with shortened time constants (minimum term
120 s, file window 600 s, appeal window 300 s, restore delay 300 s,
write-off delay 1,200 s) so the full lifecycle fits in one session. The
treasury for both deployments is
`0xD2aF69BB67d446526661A80a280820599c601ed3`, fixed at deployment.

## Offline suite

`tests/test_pure.py` (stubbed GenVM, run locally): **57 passed, 0 failed**
— every permission gate and error code, the MET / slash / appeal-overturn
/ appeal-stands settlement arithmetic to the wei, the evidence-lost cap,
the stale-appeal paths both ways, the single-pending payout rule, the
restore age and backing gates, and the shortfall-gated write-off.
Conservation is asserted after every scenario.

## Live proof — proof twin

Run 2026-11-20 with three test wallets (A: owner and treasury, B and C:
promisers). **All 8 jury assessments in the run settled on the first
attempt** — zero consensus failures, zero evidence retries. Fund
conservation was read at 11 checkpoints and held at every one.

### Beat 1 — MET, end to end

Bond 1 (promiser B, stake 20,000,000,000,000,000 wei): create tx
`0xaa72cf7e6f5c808da9b9619156d70e4b817ce2e56ac78baf846753b407887e03`,
evidence filed tx
`0x3c33a275734a567a0ff07b4a782c2ee122675d75127fdf229f24e521e0b9329a`.
Assessment tx
`0x3e12a3e788ca8ac326de04d4a8b1333f5db69adf45d25ad07bffa037a3418ca5`
returned **MET / PROMISE_PROVEN** on attempt 1. The stake was claimed
(tx `0x698f782ec9bbcbf28fe3e4981e8d43f97d5b1c42422f602d9b3228e3f83ff01f`)
and confirmed (tx
`0xed5f3a2aef514be4ef3df0719433d729e3b3b461fb7a93b5a20864f3346717e2`);
the contract balance fell by exactly 20,000,000,000,000,000 wei as the
emission landed. B's on-chain record afterwards: kept 1, kept_wei
20,000,000,000,000,000 — the full stake back, no fee taken.

### Beat 2 — NOT_MET, slashed to the pool, pool paid to the treasury

Bond 2 (promiser C, stake 20,000,000,000,000,000 wei): assessment tx
`0xe3a71a7025f03afc9e116252773b5c5d4d6eb7afd0ca3b441869aba89d3afe36`
returned **NOT_MET / REQUIREMENTS_NOT_MET** on attempt 1. No appeal was
filed; `finalize_slash` (tx
`0x7a69bb7670222b70ee9f72e7fcc0b4d0b3acc1ad3e347c52dad3df87bc6843a9`)
moved the stake to the pool (pool_amt 20,000,000,000,000,000) and C's
record shows missed 1, slashed_wei 20,000,000,000,000,000.

A first withdrawal attempt above the pool balance was rejected by the
contract with `INSUFFICIENT_POOL` (tx
`0x196933d154f266dc079927f5cd51d23ef5d946ba3b2cfae228c92cd143e9da92`)
and moved nothing. `withdraw_pool` for 5,000,000,000,000,000 wei (tx
`0x403bbb9c987f6f8c08480f7aa952d58e0e09b45c385750f13f1e8c2af185d8f8`)
credited the treasury's pot only — B's and C's pots were verified
unchanged. The treasury claimed (tx
`0x1e4e29b58b2cf4df8995f38afcf6ec162a6225ba0d33265220f8bf4da8d69950`)
and confirmed (tx
`0xec7595d3e3988ac444acacbc997fbd81d113dde96162858d0da47b983b056275`);
the contract balance fell by exactly 5,000,000,000,000,000 wei as the
emission landed. (The payout is proven by these contract-side deltas:
on Bradbury a wallet's raw balance delta across a claim window is not a
clean measure, because the claim commits roughly 0.1 GEN of sender fees
inside the same window.)

### Beat 3 — appeal, re-judged blind, verdict stands

Bond 3 (promiser B, stake 20,000,000,000,000,000 wei): first assessment
tx `0x1578ce91560eb3ec9c9169dc0b63a0396956153eb1008d10862b0c62bf155a86`
returned **NOT_MET / REQUIREMENTS_NOT_MET** on attempt 1. B appealed
(tx `0xf6117fc38dcfa4c3ae62e2b6c137fa07a14c367aa33b50c5af070500f0c45776`)
posting the appeal bond of **200,000,000,000,000 wei** (1% of the stake,
above the 0.0001 GEN floor). The appeal assessment, called by C (tx
`0x6e5ceb4e8ef833f120c3f6bf573bdc42ed0e01a6e265f2f954d476bbaa11666b`),
re-judged the identical committed evidence and returned NOT_MET on
attempt 1: outcome **APPEAL_STANDS**, state SETTLED_SLASHED, and the
pool received 20,200,000,000,000,000 wei — the stake and the appeal bond
together, to the wei. B's record: missed 1, slashed_wei
20,000,000,000,000,000.

### Beat 4 — the payout pattern, attacked live

A payout is a single emission with a single timestamp: while one stands
pending for a payee, `claim_payout` refuses a second claim.

- **PENDING_EXISTS.** Bond 4 (promiser B, stake 2,000,000,000,000,000
  wei) assessed **MET** on attempt 1 (tx
  `0x07abe92759e97f640eec0ae821b214979326302a99d0451da47677bc3888cc6f`).
  B claimed (tx
  `0x34b86ca85e2399b2b0390282c18d3e8b8f29d2c2925d4e91096431cf8260761c`);
  the emission landed in B's wallet but was never confirmed, and a
  stray transfer (tx
  `0xf3270f5cd642ca8d01a06bf6b9c9134ee46b21d24a8bb9fddbcf8ff2acc9a5a3`)
  topped the contract balance back up to the full accounted total.
  Bond 5 then settled MET, crediting B a further 1,000,000,000,000,000
  wei, and B's second `claim_payout` was rejected on chain with
  **PENDING_EXISTS** — tx
  `0xbbc051dbef25610fe9dc17444b66a290b01b79ea865d476ee76d40dcf7e8716f`
  (FINISHED_WITH_ERROR; the code is in the explorer record's decoded
  return data). The pending record stood byte-identical before and
  after — `{"amt": "2000000000000000", "since": "1795174314"}` — and B
  then confirmed the landed payout normally (tx
  `0xe4ef8c4ece14c1f941f79e67ae6ce06cedb4508f21d5ef351c1b43b7a4e03f1c`).
- **PENDING_TOO_YOUNG.** Bond 5 (promiser B) assessed **MET** on
  attempt 1 (tx
  `0x30c4bf7d7ed9a4514ffd05fc15a7265a0b4d3fe950da94c1f3dd39834c86fea2`).
  B claimed the pot (tx
  `0x0b82b17428f5a712187c63937098d3dd3b805bd2357a5a5d218bba26ba85aba0`)
  and immediately called `restore_pending`, which was rejected on
  chain with **PENDING_TOO_YOUNG** — tx
  `0xdfdb927ef6a801cc326e2198f2a2cfcda1bbb0c7ef43cc02c74db4e51571e35b`.
  The emission then landed and B confirmed it (tx
  `0x828b0ad588340338319d982ac1f8285243fdbf1adcfc9df76ef27a36dcdfe056`).

Two further bonds created during the run (bonds 6 and 7, stakes
2,000,000,000,000,000 and 1,000,000,000,000,000 wei) were settled in a
cleanup pass — both **MET / PROMISE_PROVEN** on attempt 1 (txs
`0x1825bad14bd13cfa1b7d5ae1b357a30e4e936fc730e786e0111a5d604116e497`
and
`0x75958a4e6b52e7649f5420899bd2c9b3395f9a02a47c5fcec042ad0771345bf0`) —
and the combined 3,000,000,000,000,000 wei pot was claimed and
confirmed, leaving the twin with no open bonds, no claimable pots and
no pendings.

### Conservation

`get_overview` was read at 11 checkpoints across the run; the accounted
total matched the physical balance at every one, up to the two stray
amounts below. Final twin state: 7 bonds, 5 MET, 2 slashed; locked 0,
appeal bonds held 0, claimable 0, pending 0; pool 35,200,000,000,000,000
wei (pool_in 40,200,000,000,000,000, pool_out 5,000,000,000,000,000,
total_slashed 40,000,000,000,000,000). The physical balance of
57,200,000,000,000,000 wei exceeds the accounted total by exactly
22,000,000,000,000,000 wei, fully explained: 20,000,000,000,000,000 wei
stranded by a reverted payable in an early suite run (on Bradbury a
reverted payable's value stays in the contract; it is surplus the
contract owes to nobody) plus the deliberate 2,000,000,000,000,000 wei
attack stray from Beat 4.

## Production staging

Production bond 1 (create tx
`0x636847d96a530f1003e1aaca22e72f1ac4784c01170ee7228ed552a70e9b2ced`):
promiser B, stake 20,000,000,000,000,000 wei (0.02 GEN), statement
"Publish the SkillBond contract source, offline test suite, and
live-suite results in a public repository.", requirements naming the
production contract address, deadline 7 days from creation. State OPEN,
no evidence filed. Overview after staging: locked
20,000,000,000,000,000 wei, contract balance 20,000,000,000,000,000 wei,
gap 0. Nothing else was touched on production.

## Honest bounds — what the live run did not exercise

- **The appeal-overturn branch was not exercised live.** The one live
  appeal was re-judged on its merits and the jury upheld its NOT_MET
  verdict, so the live record covers APPEAL_STANDS. The overturn path —
  stake returned in full, appeal bond refunded, pot peaking at
  20,200,000,000,000,000 wei and returning to 0 — is proven by the
  offline suite (test t39) with exact wei figures.
- **`write_off_pending` / `NO_SHORTFALL` rest on the offline suite.**
  No shortfall ever existed on the twin — every emission landed — so
  the admin write-off gate had no live occasion to fire. It is covered
  by the offline negative tests (including t54, the admin write-off
  refused with NO_SHORTFALL while the contract is fully backed).
