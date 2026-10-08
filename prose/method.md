### 2.1 The coat check

A coat check hands over a ticket before anything is left and matches it at pickup. For agent work, a ticket written before the work names the check and what done means. At pickup the claim is matched against what a record shows, never against the agent's own words. There are three outcomes:

- **shown**: a quoted line of the record shows the claim.
- **contradicted**: a line shows the opposite.
- **not shown**: no line settles it. An honest answer, not a failure.

A false done comes in two kinds: over a visible failure, or over a check that never ran (F001).

### 2.2 The kernel

The record must be one the agent cannot change: an append-only record the agent cannot write to, plus a gate that acts on it. An agent's own report is never evidence. In the relay (F005) the runner ran the hidden tests itself, and the room's hash chain verified over {{F005.c.chain_records}} records.

### 2.3 Sealing practice

1. Write the test down first: design, inputs, scorer, checks. Forecasts stay private; their hashes stay in the seal lists.
2. Seal it: a SHA-256 list, a FreeTSA time stamp, an OpenTimestamps proof that Bitcoin anchors once a block confirms.
3. Run it, keep every raw call, and seal the raw results before counting.
4. Count with the sealed scorer, with denominators and misses beside hits. Label later work exploratory. Correct by dated addendum; sealed files are never edited.

### 2.4 Status words

**Shown**: the sealed test met its pre-set rule. **Not shown**: it did not; counts are still reported. **Against**: the result went against the idea. **Exploratory**: counted after the results were known, or not in the seal. A p value is an exact McNemar test on paired outcomes unless a card says otherwise.

### 2.5 How this report is built

Each finding is a data file with the path and quoted line behind every count. Every number below is rendered from those files, and the build fails if prose carries a number no file holds. A card is never renumbered or deleted; it can be marked superseded or retracted and stays visible.
