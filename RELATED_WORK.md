# Related work

Most recent work on memory for LLM agents optimizes **retrieval**: given a
query, surface the most useful items from a store that is assumed to be
correct. LedgerBench asks a different question — what happens to that store
when the ground truth it encodes is **overturned mid-stream**, and who is
allowed to remove an item once it is invalidated. The two questions are
complementary, but they are not the same, and results on one do not
transfer to the other. The clearest recent example of the retrieval framing
is HAGE.

## HAGE (Jiang et al., 2026)

**HAGE: Harnessing Agentic Memory via RL-Driven Weighted Graph Evolution**,
Dongming Jiang, Yi Li, Guanpeng Li, Qiannan Li, and Bingzhe Li
(arXiv:2605.09942, May 2026).

HAGE reconceptualizes retrieval as query-conditioned traversal over a
unified relational memory graph. Memory nodes are shared across four
relation-specific views — semantic, temporal, causal, and entity — and each
edge carries a trainable feature vector. An LLM classifier infers the
query's relational intent, a QueryRouter MLP modulates the edge embedding,
and the whole system is trained end-to-end by policy-gradient RL against
downstream task reward, so that traversal "prioritize[s] high-utility
relational paths while softly suppressing noisy or weakly relevant
connections." On LoCoMo it reports 0.739 vs. a strongest-baseline 0.700
(LLM-as-judge), and on HotpotQA an F1 of 0.678. It is a genuine advance in
learned retrieval salience, and the authors are candid that their evaluation
covers two benchmarks and depends on the accuracy of the intent classifier.

The following are critiques of the framing and evaluation, not of the
contribution, which stands on its own terms.

### 1. Soft-suppressing "weakly relevant" edges is the wrong operation for an *invalidated* memory

HAGE's central move is to down-weight low-utility connections. That is
well-posed when a memory is merely *irrelevant* to the current query. It is
ill-posed when a memory has been *superseded* — when a requirement that was
correct becomes wrong. A superseded item is not weakly relevant; by semantic
similarity it is often the single most relevant node (the new requirement
and the one it replaced are about the same thing). Continuous down-weighting
cannot cleanly separate "stale but still an attractor" from "noise," because
the two look identical to a similarity-plus-learned-weight score. LedgerBench
was built precisely to isolate this case — two scripted requirement regime
changes over 24 tasks — and its central result is that accumulation without
**explicit, evidence-triggered retirement** degrades: an append-only memory
that is never pruned calcifies (retention held, but at 2.3× the token cost
and with coerced regressions where a stale item forced a wrong edit). Soft
suppression is a gentler version of "never remove," not a solution to it.

### 2. Both benchmarks hold ground truth fixed

LoCoMo and HotpotQA are retrieval-under-stable-truth tasks: the answer does
not change across the interaction; the difficulty is locating the right
evidence among distractors. Neither contains an event where the correct
answer to a previously-settled question is deliberately overturned. So
HAGE's gains measure better ranking of persistently-valid evidence — a real
result, but silent on memory whose contents expire. A method can top both
benchmarks and still have no mechanism for the failure mode that matters
under changing requirements. Claims about "long-horizon reasoning" should be
scoped to *long-horizon retrieval under stable truth* unless a
changing-truth benchmark is included.

### 3. RL from downstream reward can *learn* to suppress binding constraints

Edge weights in HAGE are optimized against downstream task reward. If the
reward correlates with task completion, the optimizer is incentivized to
down-weight any memory that makes completion harder — including constraints
that are correct but inconvenient. This is not a hypothetical concern.
LedgerBench measured exactly this dynamic in the one arm that let the agent
influence which memories were retired: it removed the most guardrails while
posting the highest headline score ("capture," 21 events vs. 0 in every arm
without that channel). A learned router that suppresses "low-utility" edges
is a continuous, silent version of the same channel — reward can route the
agent *around* a binding constraint and record it as an accuracy win. HAGE
reports the accuracy; its evaluation does not audit whether the suppressed
edges were noise or were constraints the reward found inconvenient. That
audit is the load-bearing measurement.

### 4. A learned router collapses proposal and authorization into one signal

LedgerBench's actual contribution is that governance of removal is
load-bearing: *who* proposes retiring a memory, *who* authorizes it, and *on
what evidence* materially change the outcome, and folding those roles
together reintroduces regressions. HAGE has no such separation — the same
RL signal that proposes down-weighting an edge also enacts it, with no
evidence gate distinguishing "superseded by a documented change" from
"low reward this epoch." Whether that separation is worth its overhead is an
open question, but it cannot be studied in an architecture that has removed
the seam.

### Complementary, and a concrete suggestion

None of this makes HAGE wrong; it makes it a solution to the retrieval half
of the problem. The two lines compose naturally — HAGE-style learned
traversal *over a governed store* is a plausible next system. To test the
concerns above, HAGE's setup could be extended with (a) a benchmark
containing explicit ground-truth reversals, and (b) an audit of the
lowest-weighted edges at convergence, checking whether any encode
still-binding constraints that reward simply made expensive. LedgerBench
supplies the first as a ready-made harness.
