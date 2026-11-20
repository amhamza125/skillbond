# SkillBond

An Intelligent Contract on GenLayer Bradbury for staking your own GEN on your own word. A promiser locks GEN on a public promise — a statement, the evidence that would prove it, and a deadline — and an AI validator jury later judges the hash-bound evidence against the requirements the promiser wrote. There is no counterparty: the only money at risk is the promiser's own stake, and the only judge is the jury.

Live contract (Bradbury, chain 4221): 0x067E9E2c911EB41F2A37B7D21333222d8df8c1e3
Deploy transaction: 0xa99d6929d081d84444e1e61210c0a98a4c10001116e669d057c96206cb4b052f
Source: `SkillBond.py` in this repository (sha256 1b650c61ce46e90f07bbf77a8494cf59177edc2b9b2d087f121c8e48f707081c)
Treasury (fixed at deployment): 0xD2aF69BB67d446526661A80a280820599c601ed3

## How a bond flows

1. **Create.** Anyone posts a bond: a statement in plain words ("publish the suite results by Friday"), the requirements text naming exactly what evidence counts, a deadline (term from 1 day to 365 days), and a stake of at least 0.001 GEN. The terms are committed at creation and can never be edited — the promise you are judged on is the promise you made.
2. **File evidence.** The promiser files 1 to 4 evidence items, each a URL plus its SHA-256, with a short note, any time up to the file deadline (the deadline plus 3 days). You file evidence against yourself, in public, with the hashes committed before the jury ever looks.
3. **Jury.** After the deadline, anyone can call `assess_bond`. The jury fetches each evidence item, hashes the raw bytes and compares them to the committed SHA-256 before reading anything — a mismatch or a failed fetch is recorded as an evidence failure, never a verdict. The verdict settles under strict equality consensus: MET with reason PROMISE_PROVEN, or NOT_MET with reason REQUIREMENTS_NOT_MET. The jury judges the evidence against the promiser's own requirements text, and no amounts ever pass through it.
4. **Settle.** MET credits the full stake back to the promiser's pot — no fee — and raises their public kept counter. NOT_MET opens a 1-day appeal window; once it passes, anyone calls `finalize_slash` and the stake moves to the community pool, raising the missed counter.
5. **Appeal.** A promiser who disagrees with a NOT_MET verdict gets one blind appeal: post an appeal bond of max(0.0001 GEN, 1% of the stake) inside the appeal window, and `assess_appeal` re-runs the jury on the identical committed inputs — the appeal jury never sees the first verdict. If the appeal overturns, the stake returns in full and the appeal bond is refunded. If it stands, the stake and the appeal bond both go to the pool. An appeal that nobody assesses for 7 days can be settled by anyone through `resolve_stale_appeal`.
6. **The pool.** Slashed stakes accumulate in the pool. The contract owner can move pool funds out with `withdraw_pool`, and they are credited to exactly one place: the treasury's pot. The treasury address is set at deployment, no method can change it, and `withdraw_pool` takes no destination address at all.
7. **Withdraw.** Pots pay out pull-style: `claim_payout` starts the transfer, `confirm_withdrawal` completes it once the GEN has landed. Only one payout per person can be in flight — while one stands pending, a second claim is refused with `PENDING_EXISTS`, so every pending is a single emission with a single timestamp. A pending can be returned to claimable by `restore_pending` only once it is at least 24 hours old **and** the contract physically holds enough GEN to back the entire pending pool, so a transfer still in flight can never be restored and paid twice. If a transfer landed but was never confirmed, `write_off_pending` clears the accounting after 7 days without re-crediting the pot; an admin-initiated write-off additionally requires an actual shortfall between the balance and what the contract owes (`NO_SHORTFALL`), so a pending can never be extinguished while the contract is fully backed.

## If evidence fails

Evidence that cannot be fetched or fails its hash check produces no verdict and moves no money. The failure is recorded on the bond, the promiser can re-file corrected evidence within 3 days of the first failure, and a bond gets at most 2 lost rounds before it settles as slashed. A promiser who never files evidence at all is settled by `finalize_unfiled` once the file deadline passes — an unproven promise counts as a missed one. Every state a bond can sit in has an exit that does not depend on the jury answering.

## Reputation

Every promiser carries a public record, readable through `get_promiser`: bonds kept, bonds missed, bonds active, and the exact wei staked, kept and slashed over their history. The record is written by settlements, not by self-report.

## Reading the contract

All state is public and readable without a wallet. Views (6): `get_bond`, `get_promiser`, `get_claimable`, `get_pending`, `get_pool`, `get_overview`. The overview reports the bond count, kept and slashed totals, and the accounted totals — locked in bonds (`lockw`), appeal bonds held (`bondw`), the pool (`poolw`), claimable (`tcw`), and in transit (`tpw`) — next to the raw contract balance, so anyone can check that the balance covers everything the contract owes.

Write methods (16): `create_bond`, `file_evidence`, `assess_bond`, `finalize_slash`, `appeal_bond`, `assess_appeal`, `finalize_unfiled`, `finalize_evidence_lost`, `resolve_stale_appeal`, `withdraw_pool`, `claim_payout`, `confirm_withdrawal`, `restore_pending`, `write_off_pending`, `transfer_ownership`, `accept_ownership`.

Every rejected call raises a named error (for example `BAD_DEADLINE`, `BOND_NOT_FOUND`, `PENDING_EXISTS`, `PENDING_TOO_YOUNG`, `NO_SHORTFALL`, `INSUFFICIENT_POOL`) and changes no state and moves no funds.

## Verification

- The contract source in this repo is byte-identical to the deployed production source (SHA-256 above, also readable from the deploy transaction).
- Offline test suite (`tests/test_pure.py`, stubbed GenVM): **57/57 passing** — every gate and error code, the settlement arithmetic for the MET, slash, appeal-overturn and appeal-stands branches, the evidence-lost cap, the single-pending payout rule, and the withdrawal backing, age and shortfall rules, with fund conservation asserted after every scenario.
- Full live proof ran on a fast-clock twin of this contract (same logic, shortened windows; twin `0x1aAc6A349341F30D81361FaF8ed0372339324D44`): a MET bond's 0.02 GEN stake returned in full; a NOT_MET bond's stake slashed to the pool and 0.005 GEN of pool funds withdrawn to the treasury's pot; an appeal re-judged blind and standing, sending the stake plus the 200,000,000,000,000 wei appeal bond to the pool; a second claim attempted while a payout stood pending rejected on chain with `PENDING_EXISTS`, and an immediate restore rejected with `PENDING_TOO_YOUNG`. All 8 jury assessments settled on the first attempt, and fund conservation held at all 11 checkpoints. Full record in `PROOF.md`.
- Production is live with one exhibit bond open: bond 1, a 0.02 GEN stake on publishing this repository, OPEN with the contract balance exactly equal to the locked total, readable on the explorer.

One plain limitation, stated up front: the jury judges the fetched evidence against the requirements as written — it cannot prove a document is genuine, and vague requirements make for vague verdicts. That is why the evidence is hash-committed in public before the deadline and why the requirements text is part of the promise itself.
