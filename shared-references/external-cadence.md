# External Cadence

External schedulers — `/loop`, `/schedule`, `CronCreate`, and any
wall-clock "wake me every N minutes" mechanism — decide **WHEN** an
agent wakes up. They do not, and must not, decide **WHO** judges the
work or **WHETHER** a result is accepted.

## Core Principle

**External cadence is pure fire-control. It is never a jury.**

A scheduler picks the firing moment. It points the agent at a task at a
chosen time. It has no opinion on correctness, quality, novelty, or
publishability, and it must never silently re-spawn an agent or drop a
verdict step in order to stay cheap or finish faster.

Rule of thumb: **cadence can DRIVE; it cannot ACQUIT.** This is the
fire-control corollary of the acceptance-gate rule
(`acceptance-gate.md`): a goal/loop may keep an agent going, but the
STOP/ACCEPT decision still belongs to whoever the acceptance gate
assigns it to — for quality/correctness verdicts, that is always a
different model family (`reviewer-independence.md`).

## Known failure mode (why this doc exists)

External cadence is genuinely useful for one shape of work — waiting on
the external world — and genuinely harmful for another — wrapping
ARIS's own internal semantic loops. The two look superficially similar
("run this skill again later"), so people reach for `/loop` on both. The
harmful case has a specific pathology:

- **Verdict re-run on a wall-clock timer.** Wrapping
  `/auto-review-loop` in `/loop 30m` does not produce 30-minutes-better
  review. It re-runs a verdict-bearing skill on a clock that has nothing
  to do with whether the artifact changed. Zero new signal, full token
  cost.
- **Thread discontinuity.** ARIS's multi-round review skills carry state
  across rounds in the reviewer's own thread: `codex-reply` reuses the
  round-1 `threadId` and the accumulated `REVIEWER_MEMORY` so the
  reviewer can check resolution against its *own* prior critique
  (`reviewer-independence.md`, Exception). An external `/loop` re-enters
  the skill from the top each tick, starting a *fresh* `threadId`. The
  reviewer loses its memory of what it already flagged; "did you fix
  round 1's gap?" becomes unanswerable.
- **Duplicated scheduling.** `/experiment-queue` already runs a
  detached server-side scheduler that polls job status every 60s and
  enforces `depends_on`. Wrapping the queue skill in an external poll
  loop duplicates that scheduler on a second, uncoordinated clock and
  invites wave-transition races the queue was built to prevent.

The fix is a clean split: external cadence for **external-world-wait**,
never for **internal semantic loops**.

## The distinction

| | External-world-wait (ADDITIVE) | Internal semantic loop (HARMFUL to wrap) |
|---|---|---|
| What it waits on | A fact in the outside world: job done, metric logged, file landed | A judgment the agent itself produces |
| What advances it | Reality changing (GPU frees, epoch logs, PDF compiles) | A model emitting a verdict |
| Owns its own loop? | No — without cadence a Claude session blocks on `sleep` | Yes — the skill already iterates internally with thread continuity |
| Cadence replaces | A blocking session burning context on a wait | Nothing — it only re-spawns and re-judges |
| Acceptance gate | Machine-checkable existence/completion (safe same-model) | Quality/correctness (must be cross-model) |

One-liner: **schedule the wait, never the verdict.**

## ADDITIVE cases (external-world-wait shape)

These replace a Claude session that would otherwise sit `sleep`-ing on
an external event. The cadence is the *only* thing the agent is waiting
for; no semantic judgment is being re-run. ARIS already validated this
pattern in production.

- **GPU / experiment job completion polling.**
  `/monitor-experiment` + `/check-gpu` on a cadence: "is the job done?
  are the GPUs still busy?" The agent wakes, reads status, and either
  reports done or sleeps again. The thing it waits on (job exit, GPU
  free) is external and machine-checkable.
- **WandB anomaly checks.** `/training-check` is *already* cron-wired:
  its SKILL.md sets itself up via `CronCreate` ("do not ask the user
  whether to set it up — just set it") to read WandB metrics every N
  minutes and catch NaN / divergence / idle GPUs early. The cadence
  exists so the agent does not have to hold a session open for the whole
  training run.
- **Experiment-queue progression visibility.** Periodically surfacing
  *where the queue is* (N done / N running / N pending) so a human can
  watch overnight progress. Read-only visibility — see the fence below
  on not re-polling the queue's own scheduler.
- **Overnight `research-pipeline` heartbeat.** A non-judgmental wake
  that checks whether the current phase is still advancing and, if a
  phase has stalled, nudges it forward. Heartbeat only — see the
  overnight-pipeline rule below.
- **Daily literature watch.** A once-a-day `/research-lit` or
  `/deepxiv` sweep for new arXiv papers in a tracked direction. The
  external fact is "the world published something new today"; the
  cadence just sets the polling rhythm.

ARIS's own `tools/watchdog.py` makes the additive shape explicit: it
aggregates per-task status into a `summary.txt` whose header documents
it as a "one-line-per-task summary for CronCreate polling." The
artifact is built *so that* an external low-frequency poller can read
completion state cheaply, without holding a session open.

### Why these are safe same-model

In every additive case the acceptance gate is **execution-completeness**
— exit code, file exists, N jobs ran, metric logged, PDF compiled. Those
are machine-checkable, so the polling agent may judge them itself
(`acceptance-gate.md`: "self-judging EXECUTION-completeness is safe
same-model"). The cadence never touches a quality/correctness verdict.

## NOISE / HARMFUL cases (wrapping internal semantic loops)

- **`/loop` around `/auto-review-loop`.** The auto-review loop *is*
  already a loop: review → implement fix → re-review, with the reviewer
  holding round-to-round memory in one `threadId`. Wrapping it in an
  external timer breaks that continuity (a fresh `threadId` per tick,
  `REVIEWER_MEMORY` reset) and fires a verdict on wall-clock time
  instead of on artifact change. Pure noise.
- **Polling `/experiment-queue` on a timer.** Duplicates the queue's
  own 60s server-side scheduler on a second clock, racing its
  wave-transition logic. Use the queue's status output for visibility;
  do not run a competing poll loop.
- **Re-asking an agent to "improve the paper" on a timer.** Quality
  does not improve on a schedule. A timed "improve again" with no new
  review signal is token burn — and if the loop also *accepts* its own
  output to decide whether to stop, it has crossed from fire-control
  into self-acquittal, which the acceptance gate forbids.

## The fence: do NOT wrap these in external cadence

Any **verdict-bearing** skill — one whose output is a judgment of
quality, correctness, support, novelty, or satisfaction — must run on
its own internal cadence with its own thread continuity, and must
terminate in the cross-model jury. Never put one inside `/loop`,
`/schedule`, or `CronCreate`:

- `/auto-review-loop` — already loops internally with reviewer memory
- `/result-to-claim` — judges whether results support a claim
- `/experiment-audit` — judges experiment integrity
- `/paper-claim-audit` — judges paper-to-evidence fidelity
- `/citation-audit` — judges bibliographic correctness
- `/peer-review` — produces a review verdict
- `/proof-checker` — judges proof validity across rounds
- `/kill-argument` — adversarial accept/reject verdict

If you find yourself wanting to schedule one of these, the thing you
actually want to schedule is the *external wait that precedes it* (job
done → then audit once), not the verdict itself.

## The affordance: natural external-wait surfaces

These are the surfaces external cadence is *for*. They wait on the
outside world and self-judge only machine-checkable completion:

- `/monitor-experiment` — poll for job completion / progress
- `/check-gpu` — poll for GPU availability and running processes
- `/experiment-queue` — **visibility only** (report position); never a
  re-poll that competes with its own scheduler
- overnight `/research-pipeline` — a **non-judgmental heartbeat + nudge**
  (see next), never a quality gate

## The overnight-pipeline rule

An overnight `research-pipeline` heartbeat may wake on a cadence,
detect that a phase has **stalled** (no progress since last tick,
process died, waiting on a freed resource), and **nudge** it forward —
unblock a stuck step, restart a dropped job, prod a phase to continue
("搞快点"). That is fire-control: it changes *when/whether work
resumes*, not *whether work is good*.

The heartbeat must **NEVER** become a quality gate. It may not decide
that a paper is good enough, that a proof holds, that a claim is
supported, or that a review is satisfied. Every such verdict stays on
its skill's own internal cadence and terminates in the cross-model jury
(`acceptance-gate.md`). The nudge keeps the pipeline moving; it does not
acquit the work the pipeline produces.

One-liner: **a heartbeat may say "keep going," never "good enough."**

## Required components (when you add external cadence to a skill)

1. **Waits on an external fact, not a self-verdict.** State the fact in
   one observable line: "job exit code present," "epoch logged to
   WandB," "PDF exists." If the thing being waited on is a model's
   judgment, cadence is the wrong tool.
2. **No verdict in the loop body.** The scheduled body may *report*
   status and *trigger the next external step*; it may not run a
   verdict-bearing skill (see the fence) as part of deciding whether to
   continue.
3. **Self-judges only machine-checkable completion.** The wake's
   accept/sleep decision must rest on exit code / file existence / count
   — never on quality or correctness (`acceptance-gate.md`).
4. **Does not duplicate an existing internal scheduler.** If the target
   already runs its own loop or server-side poller (auto-review-loop,
   experiment-queue), do not wrap it — use its status output.
5. **Preserves thread continuity for any judgment it precedes.** If the
   external wait ends in a verdict step, that verdict step runs *once*,
   in its own thread, after the wait clears — not re-entered per tick.
6. **Degrades gracefully when no scheduler exists.** External cadence is
   additive runtime sugar, never load-bearing. On a runtime with no
   `/loop` / `CronCreate`, the same work still terminates correctly via
   a blocking poll or a manual re-invocation; the cross-model jury at
   the end is identical either way (`fan-out-pattern.md`).

## Cross-references

- `acceptance-gate.md` — who is allowed to ACCEPT. Cadence drives;
  it does not acquit. The overnight nudge is bound by this rule.
- `fan-out-pattern.md` — fan-out (and cadence) are runtime accelerants
  for a prompt-level pattern; both must degrade gracefully and always
  terminate in the identical cross-model jury.
- `reviewer-independence.md` — why wrapping a multi-round review in an
  external timer breaks reviewer thread/memory continuity.
- `experiment-integrity.md` — the executor never judges its own
  experiment; a scheduled poll never upgrades to an integrity verdict.
