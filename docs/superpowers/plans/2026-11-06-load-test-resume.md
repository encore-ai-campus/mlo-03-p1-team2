# Interrupted load test recovery

**Goal:** Resume the user-authorized `load-20261106-prepare` campaign after remote disconnection, preserving all accounts, writes, evidence, and limits in `docs/loadTestPlan.md`.

**Approach:** Audit the unchanged input, account identities, database evidence and shared budget before admitting any writes. Preserve completed stages and interrupted measurements. Reauthenticate existing accounts, repeat the interrupted stage, then run the remaining stages with existing monitoring and limits. Never replay individual transactions or reset the baseline/budget.

- [x] Add regression tests rejecting pending writes, mismatched evidence, failed stages, missing accounts, and invalid stage order; verify a valid interruption selects only remaining stages. Input/account checks also execute in live preparation.
- [x] Add explicit `--resume-load` preparation and execution using the original run ID, baseline and budget. Save a recovery snapshot and an interrupted-stage summary before writing. Skip the completed consistency pilot.
- [x] Run load-runner checks (33 passed), audit live database and monitoring, archive only the confirmed stale process lock, and start one hidden process with durable output files.
- [ ] Observe the run through completion or a required stop. Keep `docs/loadTestResult.md` current and report measured results, target shortfalls and limitations.

Execution is in the existing `perf/load-test-20261106` branch because this recovery needs the current uncommitted runner corrections and ignored credentials/artifacts. Do not copy credentials to another checkout, commit unrelated changes, or reset the write budget.

Recovery finding: three service nodes restarted after the last recorded request while the generator was stopped. The initial restart guard correctly rejected continuation at 50 VU. Explicit idle-restart recovery proves restart times follow the last request, verifies stable monitoring for 30 seconds, archives the old monitoring baseline, and starts a fresh capacity segment at 1 VU. Earlier performance measurements remain visible but do not authorize larger concurrency in the new segment. Database baseline and shared budget stay unchanged.

Review: an independent reviewer found that preparation-only restart recovery committed a new segment too early. Fixed by returning after the read-only audit unless execution was explicitly requested. A lifecycle regression verifies preparation preserves state/baseline and a later execution still succeeds with the original budget. 34 runner tests passed; reviewer verified the fix. Another interruption during an empty new segment remains fail-closed and requires manual audit.

User clarification: `events` is the intended primary log collection. Keep historical `simulation` data for later cleanup. A short operator pause to confirm this destination was reconciled at 5,261 total writes / 3,826 tracking documents, with no pending requests or accounting differences. Continue the same run and shared budget from the unfinished 50-VU stage.
