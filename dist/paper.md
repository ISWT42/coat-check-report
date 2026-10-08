# The Coat Check: a living technical report on whether an agent's "done" can be trusted (paper extract)

Joshua Bauer (ISWT42), independent researcher · version 1.3.2

## 1. Summary

Can an AI agent's report of "done" be trusted? This report answers one finding at a time.

**Short version.** Small and mid-sized models often quoted the failing line and still marked the job done, or marked it done when the check never ran. In the studies here, the coat check (a ticket written before the work, matched at pickup against a record the agent cannot change) went with less false done. The studies differ in design and size, so this report does not rank them. I run and evaluate these methods myself: see Interests and independence, under Limits.

Version 1.3.2: 8 findings, 5 shown, 1 not shown, 2 exploratory.

- **F001** [exploratory] Models quoted the failing line yet said done; rewording the task moved false done onto checks that never ran.
- **F002** [shown] On one model, a coat-check ticket removed false done on never-ran logs after the do sentence.
- **F004** [exploratory] A ticket that names only the check, not the answer, also took false done to none.
- **F005** [shown] On coding jobs, a ticket plus the real check result and one fix cut false done left at the end.
- **F006** [shown] Forced yes or no made models guess; allowing not shown nearly stopped it.
- **F007** [shown] A reviewer agent followed the build agent's word; a receipt check from an unchangeable record cut false release most.
- **F008** [shown] Telling the reviewer the rule cut false release a great deal, on hosted, local and fresh claims.
- **F009** [not shown] A binding gate let few false claims through, but did not beat a told reviewer on the primary test.

## 2. Method

### 2.1 The coat check

A coat check hands over a ticket before anything is left and matches it at pickup. For agent work, a ticket written before the work names the check and what done means. At pickup the claim is matched against what a record shows, never against the agent's own words. There are three outcomes:

- **shown**: a quoted line of the record shows the claim.
- **contradicted**: a line shows the opposite.
- **not shown**: no line settles it. An honest answer, not a failure.

A false done comes in two kinds: over a visible failure, or over a check that never ran (F001).

### 2.2 The kernel

The record must be one the agent cannot change: an append-only record the agent cannot write to, plus a gate that acts on it. An agent's own report is never evidence. In the relay (F005) the runner ran the hidden tests itself, and the room's hash chain verified over 1,987 records.

### 2.3 Sealing practice

1. Write the test down first: design, inputs, scorer, checks. Forecasts stay private; their hashes stay in the seal lists.
2. Seal it: a SHA-256 list, a FreeTSA time stamp, an OpenTimestamps proof that Bitcoin anchors once a block confirms.
3. Run it, keep every raw call, and seal the raw results before counting.
4. Count with the sealed scorer, with denominators and misses beside hits. Label later work exploratory. Correct by dated addendum; sealed files are never edited.

### 2.4 Status words

**Shown**: the sealed test met its pre-set rule. **Not shown**: it did not; counts are still reported. **Against**: the result went against the idea. **Exploratory**: counted after the results were known, or not in the seal. A p value is an exact McNemar test on paired outcomes unless a card says otherwise.

### 2.5 How this report is built

Each finding is a data file with the path and quoted line behind every count. Every number below is rendered from those files, and the build fails if prose carries a number no file holds. A card is never renumbered or deleted; it can be marked superseded or retracted and stays visible.

## 3. Findings

### F001. Two kinds of false done: over a visible failure, and over a check that never ran

**Status: exploratory** (since 1.0.0). The shift between prompts was not in the sealed predictions.

*Question.* Which wrong done do models give, and does rewording the task change it?

**Result.** Under the plain report sentence Gemini 3.7 Flash called 7 of 16 failed checks done. After the do sentence it called 11 of 16 never-ran logs done (GPT-5.4 nano: 16 of 16). All 35 plain-report false done replies quoted the failing line.

**Failed check, model said done (scenarios) (of 16)**

| | Gemini 3.7 Flash | Gemini 3.8 Flash | Claude Haiku 4.5 | GPT-5.4 nano |
|---|---|---|---|---|
| T1 plain report | 7 | 5 | 0 | 0 |
| T2 with definitions | 3 | 2 | 0 | 0 |
| T3 do the work | 0 | 0 | 0 | 0 |
| T4 with proof sentence | 2 | 0 | 0 | 0 |

**Check never ran, model said done (scenarios) (of 16)**

| | Gemini 3.7 Flash | Gemini 3.8 Flash | Claude Haiku 4.5 | GPT-5.4 nano |
|---|---|---|---|---|
| T1 plain report | 0 | 0 | 1 | 6 |
| T2 with definitions | 0 | 0 | 0 | 5 |
| T3 do the work | 11 | 5 | 10 | 16 |
| T4 with proof sentence | 0 | 0 | 0 | 0 |

- Gemini 3.7 Flash, plain report against do sentence: 7 against 0, p = 0.01562 (not shown).

*Meaning.* Done covers different errors. Doing the work removed one and produced the other. A quoted line is not a receipt.

*Limits.* Invented logs, generated with a language model from fixed specifications; small and mid-sized models. The sealed paired test did not survive correction over 12 tests.

*Seal.* Bitcoin 969401 to 969403 (Appendix C).

### F002. The coat-check screen: report wordings compared on one model

**Status: shown** (since 1.0.0). One sealed comparison shown; the others not.

*Question.* Does a ticket written before the work change how often one model calls unfinished work done?

**Result.** Gemini 3.7 Flash, tools off, 1152 calls on 48 logs. After the do sentence it called 6 of 16 never-ran logs done; with the coat-check ticket, 0 of 16 (exact McNemar p = 0.03125). Plain definitions also got 16 of 16 jobs right, so the screen could not tell them apart (coat-check against quote-the-line: p = 1).

**False success on failed and never-ran logs; jobs with every log right**

| | Failed (of 16) | Never-ran (of 16) | Jobs right (of 16) |
|---|---|---|---|
| report | 4 | 0 | 12 |
| did-the-work | 0 | 6 | 10 |
| definitions | 0 | 0 | 16 |
| quote-the-line | 0 | 0 | 16 |
| coat-check | 0 | 0 | 16 |
| coat-check-did | 0 | 0 | 16 |

- never-ran: coat-check-did against did-the-work: 0 against 6, p = 0.03125.
- jobs right: coat-check against quote-the-line: 0 against 0, p = 1 (not shown).

*Meaning.* The ticket helped where the do sentence hurt, but plain definitions did as well. This screen only chose what to run next.

*Limits.* One model through a command line; versions differ in several ways. Public logs: a first attempt, planned for Gemini 3.8 Flash, searched the web and 4 answers were set aside; the rerun used Gemini 3.7 Flash with tools denied.

*Seal.* FreeTSA 2026-10-07; Bitcoin 970359 to 970373 (Appendix C).

### F004. Blind coat-check, tasks t7 and t8: the ticket names the check, not the answer

**Status: exploratory** (since 1.0.0).

*Question.* Does the ticket still work when it names only the check, not the expected result?

**Result.** With a ticket that names only the check, the models called 0, 0, 0 and 0 never-ran logs shown (t8), and 0, 0, 0 and 0 failed checks shown (t7).

**Never-ran logs called done or shown (scenarios) (of 16)**

| | Gemini 3.7 Flash | Gemini 3.8 Flash | Claude Haiku 4.5 | GPT-5.4 nano |
|---|---|---|---|---|
| T3 do the work, called done | 11 | 5 | 10 | 16 |
| t6 ticket with the value, called shown | 0 | 0 | 0 | 1 |
| t8 blind ticket, called shown | 0 | 0 | 0 | 0 |

- Gemini 3.7 Flash never-ran, T3 against t8: 11 against 0, p = 0.001 (exploratory).
- Gemini 3.7 Flash failed check, T1 against t7: 7 against 0, p = 0.016 (exploratory).

*Meaning.* The gain does not come from handing over the answer: naming the check first was enough here.

*Limits.* The job sentence still states the target in 10 of 16 jobs. Known public logs; small models.

*Seal.* FreeTSA 2026-10-07; Bitcoin 970397 to 970415 (Appendix C).

### F005. The coat-check relay: a false done travelling down a chain of coding jobs

**Status: shown** (since 1.0.0). The first primary comparison was shown; the others were not.

*Question.* Does a ticket plus the real check result reduce false done on coding jobs? Does a certifier?

**Result.** Of 36 jobs per arm, self-reporting agents left 16 false done at the end; with a ticket and one fix, 7 (exact McNemar p = 0.0039). A certifying second agent caught 9 of 9 false done shown to it, but letting it rewrite the work added errors: 11 left, from 9.

**Jobs (per arm) (of 36)**

| | False done at first claim | False done left at the end | Hidden tests passed |
|---|---|---|---|
| A self-report | 16 | 16 | 14 |
| B ticket, one fix | 9 | 7 | 21 |
| C certify before work | 9 | 11 | 18 |
| D work then certify | 7 | 9 | 24 |

- false done at the end, A against B: 9 against 0, p = 0.0039.
- A against C: 8 against 3, p = 0.2266 (not shown).
- A against D: 10 against 3, p = 0.0923 (not shown).

*Meaning.* Showing the real check result before done, and allowing one fix, cut false done. A certifier caught every false claim it saw, but rewriting undid part of the gain.

*Limits.* One run of 12 jobs; cheap models, 56 of 280 invalid replies.

*Seal.* FreeTSA 2026-10-07; Bitcoin 970397 to 970415 (Appendix C).

### F006. Forced yes or no against "not shown", across models

**Status: shown** (since 1.0.0). A later parser audit moved one count (below).

*Question.* Does forcing yes or no make models guess when evidence is missing, and does allowing "not shown" stop it?

**Result.** Across 9 models and 972 calls, Claude Opus 5.5 guessed on 27 of 27 logs missing their evidence when forced, and on 1 of 27 when "not shown" was allowed. The 7 newer models pooled: 155 guesses only when forced, 0 only when allowed (p = 4.38e-47).

**Logs: guesses where evidence is missing; right answers on intact logs (of 27)**

| | Guesses, forced | Guesses, allowed | Right, forced | Right, allowed |
|---|---|---|---|---|
| Qwen 3.5 9B | 19 | 9 | 24 | 26 |
| Gemma 4 26B | 10 | 4 | 25 | 25 |
| deepseek-v4.1-flash | 26 | 2 | 27 | 27 |
| kimi-k3 | 27 | 4 | 27 | 26 |
| GPT-6.1 Sol | 27 | 2 | 26 | 25 |
| Gemini 3.8 Flash | 20 | 3 | 27 | 26 |
| grok-4.7 | 27 | 2 | 27 | 26 |
| glm-5.3 | 20 | 5 | 27 | 27 |
| Claude Opus 5.5 | 27 | 1 | 27 | 27 |

- newer models pooled: 155 against 0, p = 4.38e-47.
- Claude Opus 5.5: 26 against 0, p = 2.98e-08.
- Qwen 3.5 9B: 10 against 0, p = 0.00195.
- Gemma 4 26B: 6 against 0, p = 0.0312.

*Meaning.* A forced binary answer manufactures guesses. Offering not shown removed most of them at no cost on intact logs.

*Record correction.* Parser audit, 7 October: Gemini 3.8 Flash forced guesses 20 of 27 became 25 of 27; the pooled test was not recomputed.

*Limits.* One call per item; my items only. A guess is defined by the forced format.

*Seal.* FreeTSA 2026-10-06; Bitcoin 970198 to 970275 (Appendix C).

### F007. A false done travels down a chain of agents; a receipt check stops most of it

**Status: shown** (since 1.0.0).

*Question.* If a build agent says done on an unbacked claim, does the next agent question it?

**Result.** Of 90 claims, 60 had no backing. On the build agent's word alone, a false done reached release on 56 of 60 (Qwen 3.5 9B) and 58 of 60 (Gemma 4 26B); with a receipt check as advice, 3 and 7. Local pair: 59 and 58 down to 14 and 16.

**False release of the unbacked claims (hosted | local) (of 60)**

| | Qwen hosted | Qwen local | Gemma hosted | Gemma local |
|---|---|---|---|---|
| G0 word only | 56 | 59 | 58 | 58 |
| G1 word and log | 16 | 20 | 14 | 17 |
| G2 word and receipt check | 3 | 14 | 7 | 16 |

- hosted Qwen 3.5 9B, G0 against G2: 53 against 0, p < 0.001.
- local Qwen3-4B, G0 against G2: 45 against 0, p < 10^-12.
- local Gemma-4-E4B, G0 against G2: 42 against 0, p < 10^-12.

*Meaning.* The next agent never questioned the one before: after a hold, release happened 0 times. A check against a record the agent cannot change helped most.

*Limits.* One scripted build message; run records withheld, so seals cannot be checked against content. The audit moved the hosted gate's false pass from 3 of 60 to 4 of 60.

*Seal.* FreeTSA 2026-10-06; Bitcoin 970158 to 970187 (Appendix C).

### F008. A reviewer told the rule closes much of the gap

**Status: shown** (since 1.0.0).

*Question.* If the reviewer is told the rule, how many false claims does it let through?

**Result.** False release of the unbacked claims, G1 then G1T: hosted Qwen 3.5 9B 15 to 7, hosted Gemma 4 26B 13 to 3; local Qwen3-4B 20 to 9, Gemma-4-E4B 17 to 6; on fresh claims 29 to 10 and 21 to 9.

**False release: reviewer with the log (G1) or told the rule (G1T) (of 60)**

| | G1 | G1T |
|---|---|---|
| S11 hosted Qwen 3.5 9B | 15 | 7 |
| S11 hosted Gemma 4 26B | 13 | 3 |
| S11L local Qwen3-4B | 20 | 9 |
| S11L local Gemma-4-E4B | 17 | 6 |
| Gate test Qwen3-4B (fresh claims) | 29 | 10 |
| Gate test Gemma-4-E4B (fresh claims) | 21 | 9 |

- hosted Qwen 3.5 9B: 8 against 0, p = 0.00781.
- hosted Gemma 4 26B: 11 against 1, p = 0.00635.
- local Qwen3-4B: 12 against 1, p = 0.00342.
- local Gemma-4-E4B: 12 against 1, p = 0.00342.
- fresh claims, Qwen3-4B: 20 against 1, p = 2.1e-05 (exploratory).
- fresh claims, Gemma-4-E4B: 13 against 1, p = 0.00183 (exploratory).

*Meaning.* Much of F007's gap was an untuned reviewer. The told-rule sentence and the ticket both ask for a line that shows the claim.

*Limits.* Small models; the sentence was written after F007.

*Seal.* FreeTSA 2026-10-06 to 2026-10-07; Bitcoin 970187 to 970333 (Appendix C).

### F009. A binding gate against a reviewer told the rule: not shown

**Status: not shown** (since 1.0.0). The sealed primary comparison was not shown; gate against advice-only was secondary.

*Question.* On fresh claims, does a binding gate let fewer false claims through than a told reviewer?

**Result.** On 90 fresh claims the binding gate released 5 and 5 of 60 false claims; the told reviewer 10 and 9. The primary comparison gave p = 0.125 for both models: not shown. The gate held back 2 of 30 true claims.

**False release: G1 log, G1T told rule, G2 advice, G3 gate (of 60)**

| | G1 | G1T | G2 | G3 |
|---|---|---|---|---|
| Qwen3-4B | 29 | 10 | 14 | 5 |
| Gemma-4-E4B | 21 | 9 | 20 | 5 |

- primary, Qwen3-4B, G1T against G3: 6 against 1, p = 0.125 (not shown).
- primary, Gemma-4-E4B, G1T against G3: 4 against 0, p = 0.125 (not shown).
- Qwen3-4B, G2 against G3: 9 against 0, p = 0.00391 (exploratory).
- Gemma-4-E4B, G2 against G3: 15 against 0, p = 6.1e-05 (exploratory).

*Meaning.* The gate let few through, but this size cannot show a modest gap over a told reviewer; advice alone was much weaker.

*Limits.* Small models; invented claims, generated with a language model from fixed specifications; the key is withheld. Each held-back true claim is a job for a person.

*Seal.* FreeTSA 2026-10-07; Bitcoin 970271 to 970333 (Appendix C).

## 4. Limits and threats to validity

- **Small models, invented items.** Most tests use small or mid-sized models. The test items were generated with a language model from fixed specifications, not drawn from real work. Results may not carry to larger models or real logs.
- **Public items.** The Kaggle logs and answers are public, so a model with web access could look them up (F002).
- **My work only, no outside replication yet.** A time stamp shows a file existed by then, not that no other version was sealed.
- **Small counts, many tests.** Most tests are exact paired tests on a few dozen items, uncorrected unless a card says so.
- **Counts moved by audit.** A parser audit moved a few counts after sealing; cards record the correction, and no headline reversed.
- **Local checks only.** Quotes were checked against local copies, not live public copies.
- **Withheld.** Forecasts and some run records are not published.

### Interests and independence

I develop the coat-check method and receipt tools, and I may offer paid services built on them. My evaluations here of my own methods and tools are developer-led, not independent validation. Outside review and replication are invited: a replication kit exists and will be published, with its link added here. I hold no investments in AI companies.

## 5. What's next

- **Q001** [open] Replicate on fresh items, held back until they run.
- **Q002** [open] Does the ticket hold on longer real logs and larger models?
- **Q003** [open] Pair "Report whether" and "Check that" on identical logs.
- **Q004** [open] Why did a certifier that rewrote the work add errors? Test certify-only.
- **Q005** [open] Compare the binding gate with a told reviewer on enough claims to see a modest gap.
- **Q006** [open] Recompute the pooled forced-choice test with the audited Gemini 3.8 Flash count.
- **Q007** [closed] The harness comparison ended as the OpenAI pair only: too few errors to show a difference; I closed the Claude pair on 8 October.
- **Q008** [answered by a finding] Earned Agency Bench: run once on small models; the results are in the findings listed here.
- **Q009** [open] A second bench on messy real logs, with an imperfect checker that is not handed the test line.
- **Q010** [open] Replicate the bench with other models and fresh jobs. The sealed code is in the public record.

**Acknowledgement.** Version 1.3.0 was revised after an outside methods review, 8 October 2026.
