# ARC-AGI-3 baselines: predictions (written before any baseline run)

Date: 2026-11-08. Toolkit arc-agi 0.9.9, 25 public games, run locally.

## Setup
- Each game: 64x64 frames, 16 colours, 6-10 levels, actions 1-7 (ACTION6 = click at x,y).
- Official per-level score = min(115, 100 * (human_baseline_actions / agent_actions)^2);
  unfinished level = 0; game score = level-index-weighted mean; overall = mean over games.
- Budget: 10,000 actions per game per run. 3 seeds per agent.
- A probe of 2,000 random actions per game already showed: level 1 reached on 3/25 games
  (r11l, cd82, sp80). Predictions below are about the full 10k-action runs.

## Agents
- RANDOM: uniform over available actions; clicks at uniform random pixels.
- EXPLORER: no learning across games. Hashes each frame as a state, builds a graph of
  (state, action) -> next state, tries untried actions first, clicks only on object
  centroids (connected same-colour regions), walks the known graph to the nearest state
  with untried actions, avoids transitions that led to GAME_OVER, clears the graph on a new level.

## Predictions
P1. RANDOM completes at least one level on <= 6 of 25 games; overall score < 0.2.
P2. EXPLORER completes at least one level on more games than RANDOM: 8-14 of 25.
P3. EXPLORER overall score is still small: < 3 (the squared efficiency term punishes the
    hundreds of exploratory actions it needs even when it succeeds).
P4. Neither agent completes level 2 on more than 4 games.
P5. EXPLORER's main failure: games whose frame contains a counter/timer, so every frame is
    a "new state" and the graph never closes (state explosion). We expect the explorer's
    distinct-state count to be close to its action count on those games.

## Results (added after the runs; 3 seeds x 25 games x 10,000 actions; score on the official 0-100 scale)
| | mean score | games with >= 1 level | games with >= 2 levels |
|---|---|---|---|
| RANDOM | 0.103 (seeds 0.193 / 0.005 / 0.112) | 7 / 6 / 6 | 0 / 0 / 1 |
| EXPLORER | 0.095 (seeds 0.066 / 0.020 / 0.200) | 10 / 10 / 11 | 3 / 3 / 2 |

Scores were checked against the toolkit's own EnvironmentScoreCalculator: 150/150 match
(after fixing my first version, which capped the game score at 100 instead of at the
completed-level weight share).

- P1 mostly right: score < 0.2 held; games with a level was 7 on one seed (predicted <= 6).
- P2 right (10-11). P3 right (0.095). P4 right (max 3).
- P5 partly wrong: state explosion is real on some games (re86, tr87: ~0.95 new states per
  action, never solved), but tn36 was solved at 0.93, and many failures have a CLOSED graph
  (bp35 0.10, sk48 0.07, dc22 0.24) - the agent revisits the same states and still finds no win.
- Main finding: exploration coverage does not translate into score. The explorer reaches
  more levels, but needs thousands of actions per level, and the squared efficiency term
  makes that worth ~0. Both agents' means are dominated by one or two lucky fast solves
  (r11l, sp80), so seed-to-seed variance is larger than the difference between agents.


# Step A: rule-learning agent, transfer vs reset (predictions written 2026-11-10, before any run)

## What was observed before writing these (probes, not runs of the agent)
- 22 of 25 games have a step counter: a bar on one frame edge (row 0, row 63, col 0, col 63,
  rows 61-62, or row 53) that changes 1-2 pixels on every action, including actions that do
  nothing else. Every such step looks like a new frame to a plain frame hash.

## Agent (RULE)
- Same graph exploration as EXPLORER, plus:
  1. Clock mask: a row or column where small (<= 4 px) changes keep landing on new pixels is
     marked as a counter and left out of the state hash.
  2. Objects: connected same-colour regions, described by colour, size and bounding-box shape.
  3. Effect statistics: for each plain action, and for clicks on each object type, how often it
     changed the (masked) frame. In every new state, untried actions are ordered by predicted
     chance of doing something (unseen types first, then likely-effective, then likely no-ops).
     Nothing is ever removed, so the search stays complete.
- Two modes, identical code and seed:
  - RESET: effect statistics wiped at every new level.
  - TRANSFER: effect statistics kept across levels.
  Up to the first completed level, both modes are the same run action for action, so every
  difference after that is caused by the carried-over knowledge alone (a paired comparison).
- Budget 10,000 actions per game, 3 seeds, same 25 games.

## Predictions
A1. Clock masking: on the 10 games where EXPLORER had > 0.5 new states per action
    (cd82, cn04, ka59, r11l, re86, sp80, tn36, tr87, vc33, wa30), RULE at least halves that
    ratio on >= 5 of them. tr87 (no edge counter found) stays > 0.8.
A2. RULE clears level 1 on more games than EXPLORER (10-11): 12-16 of 25 per seed.
A3. Paired transfer vs reset, on game-seeds where level 1 was cleared: median actions spent
    on level 2 at least 30% lower with TRANSFER, and TRANSFER clears level 2 on at least as
    many of them.
A4. Overall score stays < 1 for both modes.
A5. At least one game shows negative transfer (TRANSFER needs > 30% more actions on level 2
    than RESET, or fails a level that RESET clears).


## Step A results (added after the runs; 3 seeds x 25 games x 10,000 actions; official 0-100 scale)
| | mean score | games >= 1 level | games >= 2 levels | total levels |
|---|---|---|---|---|
| EXPLORER | 0.095 | 10 / 10 / 11 | 3 / 3 / 2 | 13 / 13 / 13 |
| RULE, RESET | 0.271 (0.205 / 0.245 / 0.364) | 16 / 15 / 15 | 6 / 6 / 6 | 25 / 23 / 22 |
| RULE, TRANSFER | 0.275 (0.172 / 0.288 / 0.365) | 16 / 15 / 15 | 5 / 6 / 5 | 22 / 24 / 21 |

Scores checked against the toolkit's EnvironmentScoreCalculator: 300/300 match.
Pairing check: on all 46 game-seeds where level 1 was cleared, both modes cleared it in exactly
the same number of actions (0 mismatches), so the comparison after level 1 is clean.

- A1 WRONG (narrowly): states-per-action halved on 4/10 (cd82, r11l, tn36, vc33), not >= 5.
  The counter detector is conservative: on cn04, ka59, wa30 it found no counter line at all.
  tr87 stayed > 0.8 (0.86), as predicted.
- A2 RIGHT: level 1 cleared on 15-16 games (explorer 10-11).
- A3 WRONG: 16 game-seeds where both modes cleared level 2. TRANSFER used fewer actions on
  12 of them, more on 4 (sign test, one-sided p ~ 0.04). Per pair, the median TRANSFER/RESET ratio
  is 0.92 and the geometric mean 0.80, i.e. 8-20% fewer actions, not >= 30%. (The raw medians
  553 vs 1220 compare different games and overstate the effect.) TRANSFER cleared level 2 on
  16 game-seeds, RESET on 18, so the "at least as many" part also failed.
- A4 RIGHT: both modes < 1 (0.27).
- A5 RIGHT: negative transfer in 4 cases: lf52 on all 3 seeds (TRANSFER fails level 2 on seeds 0
  and 2 and is slower on seed 1, 8,058 vs 6,087 actions; RESET clears it in ~6,100) and cd82 seed 1
  (3,649 vs 1,878). [Corrected 2026-11-10: first written as "TRANSFER never clears level 2", which was wrong for seed 1.]

## What Step A shows
- Most of the gain over EXPLORER (score x2.9, level 1 on ~50% more games) is learning WITHIN a
  level: ignoring step counters and trying likely-effective actions first. That is real-time
  learning, but not yet transfer.
- Carried-over knowledge helps a little and usually (12/16), and hurts badly on one game every
  time (lf52): what was learned on level 1 is wrong for level 2, and the agent has no way to notice.
  This is the precise gap Step B's surprise check is meant to close.
- The small, consistent saving on lp85 (~14 actions on every seed) is what pure "which actions
  do nothing" knowledge buys; the large savings (cd82 s2 559 vs 6,050; tu93 s1 32 vs 130) come
  most likely from the changed search order reaching the right region sooner (not yet verified; one seed each, so partly luck).


# Step B: surprise check on carried-over knowledge (predictions written 2026-11-10, before any run)

## Diagnosis of lf52 first (seed 0, before designing Step B)
- What level 1 taught: clicks on 1x1 colour-1 objects change the frame 58% of the time;
  clicks on 4x4 colour-14 objects 43% (only 5 tries).
- On level 2, RESET (knows nothing) tries every object type early, finds the 4x4 colour-14
  objects work ~90% of the time and leans on them; it clears level 2 after 6,425 actions.
- TRANSFER keeps ranking the many 1x1 objects first in every state (its old estimate says so),
  and spends most of its budget clicking them. Its level-2 rates (1x1: 74%, 4x4: 58%) never
  strongly contradict the old estimate, so the old ranking survives. It does not clear level 2.
- So lf52 is less "a wrong rule" than "a mis-ranking that is never re-checked". In both modes,
  long stretches find 0 new states per 1,000 actions: the search keeps re-walking a closed
  graph to try remaining clicks. (Also noted: actions taken while walking a planned path count
  toward the effect statistics. Left unchanged so Step B stays comparable to Step A.)

## Agent (SURPRISE mode) - same code as RESET/TRANSFER; differs only from level 2 on
1. Trust but verify: at a new level, every carried action kind counts as unverified and is
   tried early (like an unseen kind) until it has 2 tries on this level.
2. Surprise test per kind: two predictions are kept for every outcome on this level, one from
   old + new evidence and one from new evidence only. When the new-only prediction explains this
   level's outcomes better by a clear margin (log Bayes factor > 2), the old evidence for that kind
   is dropped. Each drop is logged as a surprise event.
3. Level-wide switch: if more than half of the kinds verified on this level get dropped, all
   old evidence is dropped (the level is treated as having new rules).
Again identical to the other modes up to level 1, so comparisons with RESET and TRANSFER are paired.

## Predictions
B1. lf52: SURPRISE clears level 2 on at most 1 of 3 seeds (TRANSFER 0/3, RESET 3/3). Reason:
    per the diagnosis, the old rules there are mis-ranked rather than clearly contradicted, so the
    surprise test rarely fires; only the early re-check (1) can help.
B2. Over the game-seeds where level 1 is cleared, SURPRISE clears level 2 on at least 17
    (TRANSFER 16, RESET 18), and on pairs where SURPRISE and RESET both clear level 2,
    SURPRISE uses fewer actions on at least 60% of them.
B3. Self-knowledge test: surprise events per level are higher on the game-seeds where transfer
    hurt (lf52 x3, cd82 s1) than the median over all game-seeds that reach level 2.
B4. Overall score within +/- 0.03 of TRANSFER (0.275): the score is still dominated by level 1.
B5. Cost of re-checking: on lp85, TRANSFER's saving over RESET on level 2 (~14 actions per seed)
    shrinks to <= 7 with SURPRISE.


## Step B results (added after the runs; 3 seeds x 25 games x 10,000 actions)
| | mean score | games >= 2 levels | level 2 cleared (of 46 game-seeds with level 1) |
|---|---|---|---|
| RESET | 0.271 | 6 / 6 / 6 | 18 |
| TRANSFER | 0.275 | 5 / 6 / 5 | 16 |
| SURPRISE | 0.300 (0.171 / 0.261 / 0.470) | 6 / 6 / 6 | 18 |

Checks: scores 375/375 match the toolkit calculator; level-1 pairing with RESET 0 mismatches;
TRANSFER re-run after the code change reproduced its earlier results exactly (regression check).

- B1 WRONG (in the good direction): SURPRISE cleared lf52 level 2 on 3/3 seeds (9,593 / 6,257 /
  6,562 actions; RESET 6,425 / 6,087 / 5,846; TRANSFER failed on 2 of 3). The surprise test did
  fire there (3 old rules dropped on level 2 every seed), so my diagnosis-based pessimism was wrong.
- B2 WRONG: level 2 cleared on 18 (>= 17 held), but on the 18 pairs both cleared, SURPRISE used
  fewer actions than RESET on only 9 (50%, not >= 60%). Per pair median ratio vs RESET 1.00,
  geometric mean 0.96. Against TRANSFER: fewer on 6 of 16, more on 10 (geo-mean 1.16).
- B3 RIGHT as stated, but weak: the hurt cases average 2.5 surprise events on level 2 vs a median
  of 1 (lf52 3/3 above, cd82 s1 not). But the signal is not specific: dc22 (where transfer HELPED)
  fires most (6 every seed), and sp80, g50t, ls20 fire as often as lf52.
- B4 RIGHT: +0.026 vs TRANSFER, within +/- 0.03. Almost all of it is one run: tu93 seed 2, level 2
  in 18 actions instead of 37 (game score 0.84 -> 3.52). Not a real improvement.
- B5 RIGHT: on lp85 the saving over RESET disappeared (-10 / -2 / -10 actions, vs +14 for TRANSFER).

## What Step B shows
- The surprise check removes the damage (lf52 recovered on every seed, level 2 count back to 18),
  but it also removes the benefit: overall it behaves like starting fresh (ratio 1.00 vs RESET).
  Re-checking everything costs about what transferring saved.
- The agent's "this rule no longer holds" signal fires where things changed, but it also fires
  where the old knowledge was still useful (dc22), so it cannot yet tell harmful change from
  harmless change. That is the open problem: knowing WHICH of its knowledge is wrong, cheaply.


# Step C: what costs the benefit, and selective re-checking (predictions written 2026-11-10, before any run)

## Design
- Games: the 6 where any mode ever reached level 2 (cd82, dc22, lf52, lp85, tu93, vc33).
  10 seeds (0-9) instead of 3, budget 10,000 actions per game. About 60 paired level-2 comparisons.
- Five modes, same code, identical up to the first completed level:
  - RESET, TRANSFER: as in Step A.
  - SURPRISE: as in Step B (every carried kind re-checked early + drops when contradicted).
  - DROPONLY: drops when contradicted, but no forced re-checks (observation is free).
  - SELECTIVE: drops when contradicted; forced re-check only for kinds tried fewer than 10 times
    on earlier levels (poorly established knowledge). Well-established kinds are trusted at once.
- Effect measure: per pair, level-2 actions of mode X vs RESET; summary = share of pairs where X
  used fewer actions (sign test), median and geometric-mean ratio. Unfinished level 2 counted
  separately.

## Predictions
C1. Most of Step B's lost benefit comes from the forced re-checks: DROPONLY beats RESET on more
    pairs than SURPRISE does, and its geometric-mean ratio vs RESET is at most 0.92 (TRANSFER was 0.80
    in Step A). But DROPONLY does NOT fix lf52: it clears lf52 level 2 on at most 5 of 10 seeds.
C2. SELECTIVE clears lf52 level 2 on at least 7 of 10 seeds, and on lp85 its level-2 actions are
    within 5 of TRANSFER's (median over seeds).
C3. SELECTIVE beats RESET on at least 60% of pairs where both clear level 2, and clears level 2 on
    at least as many game-seeds as RESET. This is the target result: transfer that is both helpful and safe.
C4. The surprise signal stays unspecific: on dc22, SELECTIVE logs at least as many surprise events on
    level 2 as on lf52 (median over seeds).


## Step C results (added after the runs; 5 modes x 10 seeds x 6 games, 10,000 actions)
Checks: 0 mismatches against the earlier full runs for the seeds/modes they share (exact
reproduction); 0 level-1 pairing mismatches; 0 failed runs. 60 game-seeds cleared level 1.

Level 2 vs RESET (pairs where both cleared level 2; p = one-sided sign test that X uses fewer actions):
| mode | level 2 cleared (of 60) | fewer / more | p | median ratio | geo-mean ratio |
|---|---|---|---|---|---|
| RESET | 58 | - | - | 1.00 | 1.00 |
| TRANSFER | 52 | 36 / 15 | 0.002 | 0.95 | 0.89 |
| SURPRISE | 57 | 29 / 27 | 0.45 | 1.00 | 0.93 |
| DROPONLY | 52 | 36 / 15 | 0.002 | 0.96 | 0.94 |
| SELECTIVE | 55 | 29 / 24 | 0.29 | 0.99 | 0.89 |

Per game, level 2 cleared of 10: lf52 RESET 9, TRANSFER 3, SURPRISE 10, DROPONLY 3, SELECTIVE 9;
cd82 RESET 9, TRANSFER 9, SURPRISE 7, DROPONLY 9, SELECTIVE 6. All other games 10/10 in every mode.

- C1 PARTLY WRONG: DROPONLY beat RESET on more pairs than SURPRISE (36 vs 29), and did not fix
  lf52 (3/10) - both right. But its geometric-mean ratio was 0.94, not <= 0.92.
- C2 HALF WRONG: SELECTIVE fixed lf52 (9/10, predicted >= 7) - right. On lp85 it still cost a
  median of 24 actions vs TRANSFER (predicted <= 5) - wrong: several lp85 kinds have < 10 earlier tries.
- C3 WRONG: SELECTIVE beat RESET on 55% of pairs (needed >= 60%; p = 0.29) and cleared level 2 on
  55, not >= 58. It lost ground on cd82 (6/10 vs 9/10).
- C4 RIGHT: median surprise events on level 2 were 6 on dc22 vs 2.5 on lf52.

## What Step C shows (the clearest result so far)
1. With 10 seeds, transfer clearly helps: fewer level-2 actions on 36 of 51 pairs (p = 0.002),
   ~11% fewer on average (geo-mean 0.89). Step A's 3-seed estimate (8-20%) was in the right range.
2. Its one systematic failure (lf52, 7/10 seeds fail) is NOT fixed by dropping contradicted rules:
   DROPONLY's drops fire on lf52 (2-5 per seed) and it still fails 7/10. It IS fixed by an early
   re-check of thinly supported rules (SELECTIVE 9/10, SURPRISE 10/10). Noticing a contradiction in
   passing comes too late; the agent has to go and look.
3. Re-checking has a price that shows up elsewhere (lp85 +24 actions, cd82 fewer clears), so no
   version yet gets transfer's benefit and safety together. Within this design there is a direct
   trade-off between "use what I know" and "check what I know".
4. The surprise signal reflects how much changed, not whether the change matters (dc22 fires most
   while transfer helps there).


# Step D: Rudakov et al.'s graph explorer, reproduced offline (results added 2026-11-10, no predictions written - a reproduction)
- 3 seeds with the re-initialisation fix + 1 seed exactly as published; 25 games, 10,000 actions. Scorer 450/450.
- Fixed: score 0.328 (0.233 / 0.533 / 0.219), level 1 on 10 games every seed, level 2 on 4-5, levels 14-18.
  As published: 0.226, 6 games, median 9,088 errors per game (the loop never re-initialises after an error).
- Not stronger than our rule agent here (0.27, level 1 on 15-16, levels 21-25), but good on different games:
  theirs only: ar25 (2 levels), bp35, ka59 (1 seed); much faster on sp80 (124 vs 948) and r11l (20 vs 73).
  ours only: dc22, g50t, lf52, ls20, su15, tn36, tu93; faster on lp85 (28 vs 184).

# Step E: combined agent (predictions written 2026-11-10, before any run)
## Design
- Our rule agent (graph, counter mask, learned effect statistics, reset/transfer) plus two pieces of theirs:
  1. their shape-based status-bar mask (segments within 3 cells of an edge that are long and thin, or come
     with >= 3 identical twins on the edge), computed from the first frame of each level and left out of the
     state, on top of our change-based counter mask;
  2. their salience tiers as the starting rank of action kinds never tried: tier 0 = salient colour (6-15) and
     medium size (2-32 cells each way), 1 = medium size, 2 = salient colour, 3 = other, 4 = status bar.
     Unseen kinds start at 1.0 - 0.1 x tier instead of 1.0; once tried, our learned estimate takes over.
     Up to 80 click targets per state, now chosen by tier first, then size.
- If the map runs out with no win, both masks are dropped for that level (as before).
- Modes reset and transfer, 3 seeds, 25 games, 10,000 actions.
## Predictions
E1. The combined agent clears level 1 on 17-19 games per seed (ours 15-16, theirs 10).
E2. Mean score above 0.30 over 3 seeds (ours 0.27, theirs 0.33 with one lucky seed), still below 1.
E3. It keeps our wins: on the 7 games only ours solved (dc22, g50t, lf52, ls20, su15, tn36, tu93) it clears
    level 1 on at least 6, on every seed.
E4. It reaches level 2 on at least 7 games per seed (ours 5-6, theirs 4-5).
E5. sp80: median level-1 actions below 400 (ours 948, theirs 124).


## Step E results (added 2026-11-11; 3 seeds x 25 games x 10,000 actions; scorer 600/600; level-1 pairing 0 mismatches)
| | mean score (per seed) | level 1 cleared | level 2 cleared | total levels |
|---|---|---|---|---|
| ours, RESET | 0.271 (0.205 / 0.245 / 0.364) | 16 / 15 / 15 | 6 / 6 / 6 | 25 / 23 / 22 |
| Rudakov (fixed) | 0.328 (0.233 / 0.533 / 0.219) | 10 / 10 / 10 | 4 / 4 / 5 | 14 / 14 / 18 |
| combined, RESET | 0.597 (0.718 / 0.427 / 0.646) | 17 / 17 / 17 | 6 / 6 / 5 | 26 / 26 / 25 |
| combined, TRANSFER | 0.547 (0.570 / 0.427 / 0.644) | 17 / 17 / 17 | 5 / 6 / 5 | 26 / 26 / 24 |

- E1 RIGHT: level 1 on 17 games every seed.
- E2 RIGHT: mean 0.60 (reset) and 0.55 (transfer), every seed above 0.30, below 1. More than double ours.
- E3 RIGHT: our-only games kept: 6 / 7 / 7 of 7 (g50t missed on seed 0).
- E4 WRONG: level 2 on 5-6 games per seed, not >= 7.
- E5 WRONG: sp80 level 1 in 713-743 actions (theirs 24-184), not < 400.
Where the gain comes from (median level-1 actions, ours -> combined): m0r0 1,399 -> 51; bp35 never -> 115;
ar25 7,966 -> 1,669; lf52 126 -> 39; tn36 44 -> 22; r11l 73 -> 23; cn04 solved on 1 seed (33). Losses: ft09
689 -> 2,458; cd82 645 -> 1,160; ka59 (theirs, 1 seed) not kept.
Transfer inside the combined agent (paired, 3 seeds): both cleared level 2 on 15 game-seeds, transfer fewer on 9;
level 2 cleared reset 17, transfer 16; lf52 again fails under transfer (levels 1/2/1 vs 2/2/2). Same pattern as
Steps A and C, too few pairs to say more.


# Step F: Step C repeated inside the combined agent (predictions written 2026-11-11, before any run)
## Design
- Same as Step C (5 modes: RESET, TRANSFER, SURPRISE, DROPONLY, SELECTIVE; 10 seeds; the 6 games that reach
  level 2: cd82, dc22, lf52, lp85, tu93, vc33; 10,000 actions), but every mode runs on the combined agent.
- Same measures: per pair, level-2 actions vs RESET (sign test, median and geometric-mean ratio); level-2 clears.
- Question: do Step C's findings hold in an agent with twice the score?
## Predictions
F1. Transfer still helps, but less: TRANSFER beats RESET on at least 55% of pairs where both clear level 2, with a
    geometric-mean ratio above 0.89 (Step C: 0.89). Reason: the salience tiers already give a good starting order,
    so some of what transfer carried over is now known from the start.
F2. The lf52 failure persists: TRANSFER clears lf52 level 2 on at most 5 of 10 seeds; RESET on at least 8.
F3. Re-checking still fixes it: SURPRISE and SELECTIVE each clear lf52 level 2 on at least 8 of 10 seeds.
F4. Passive dropping still does not: DROPONLY clears lf52 level 2 on at most 5 of 10 seeds.
F5. The trade-off persists: no version both clears level 2 within 2 game-seeds of RESET and beats RESET on at
    least 60% of pairs.


## Step F results (added 2026-11-11; 5 modes x 10 seeds x 6 games, combined agent, 10,000 actions)
Checks: 0 mismatches against the Step E full runs for shared seeds/modes; 0 level-1 pairing mismatches; 0 failed
runs; 60 game-seeds cleared level 1. (Scores use the same game_score function verified 600/600 on the full runs.)

| mode | level 2 cleared (of 60) | fewer / more vs RESET | p | median ratio | geo-mean ratio | lf52 level 2 (of 10) |
|---|---|---|---|---|---|---|
| RESET | 58 | - | - | 1.00 | 1.00 | 9 |
| TRANSFER | 54 | 34 / 19 | 0.027 | 1.00 | 0.99 | 5 |
| SURPRISE | 56 | 31 / 24 | 0.21 | 1.00 | 0.98 | 8 |
| DROPONLY | 51 | 28 / 21 | 0.20 | 1.00 | 1.13 | 5 |
| SELECTIVE | 57 | 31 / 23 | 0.17 | 1.00 | 1.14 | 9 |

- F1 RIGHT: TRANSFER beats RESET on 64% of pairs (p = 0.03), and the average saving shrank: geo-mean 0.99
  (Step C: 0.89). It wins more often than it loses, but by small margins.
- F2 RIGHT: lf52 level 2 - TRANSFER 5/10, RESET 9/10.
- F3 RIGHT: SURPRISE 8/10, SELECTIVE 9/10.
- F4 RIGHT: DROPONLY 5/10 (its drops fire on lf52, 2-4 per seed, as in Step C).
- F5 RIGHT: no version is both as safe as RESET (within 2 clears) and better on >= 60% of pairs
  (SURPRISE 56 clears / 56%; SELECTIVE 57 / 57%; TRANSFER 64% but 54 clears).
Other: SELECTIVE's lp85 cost fell to a median 6 actions (Step C: 24). Re-checking still hurts cd82
(SELECTIVE median 6,701 vs RESET 2,839; DROPONLY 6/10 clears). The surprise signal still fires most on dc22
(median 6) and cd82 (5.5), more than on lf52 (3).

## What Step F shows
Step C's qualitative findings replicate in an agent with roughly twice the score: carried knowledge wins more
often than not, its failure on lf52 comes from a thinly supported rule, only active re-checking repairs it, and
that repair costs what transfer gains. What changed: the size of transfer's benefit, which nearly vanishes once the
agent starts from a good built-in ranking of what to click.


# Step G: re-check only when the answer could change the decision (predictions written 2026-11-11, before any run)
## Idea
Steps C and F: re-checking every carried rule (SURPRISE) or every thinly tested one (SELECTIVE) repairs lf52 but
costs what transfer saves. New mode VOI ("value of information"): information is only worth paying for if it could
change what the agent does. When a carried action kind first appears in a state on a new level, the agent compares
its uncertainty with the other kinds in that state:
- each kind's chance of doing something gets a plausible range (posterior mean +/- 2 standard deviations, from old
  plus new evidence; a never-tried kind is a fixed point at its starting rank);
- a carried kind is re-checked (tried 2 times early, as in SURPRISE) only if its range overlaps another kind's range,
  so their order could be the wrong way round, and it is the less certain of the two;
- otherwise it is trusted at once. Contradicted rules are still dropped (as in all re-check modes).
Decided once per kind per level. No randomness added, so VOI is identical to the other modes up to level 1 and
pairs with the Step C and Step F runs (same seeds, same 6 games, 10,000 actions).
Runs: VOI on the combined agent (10 seeds) and on our original agent (10 seeds).
## Predictions (combined agent unless stated)
G1. VOI clears lf52 level 2 on at least 8 of 10 seeds (TRANSFER 5, RESET 9).
G2. VOI clears level 2 on at least 56 of 60 game-seeds (RESET 58).
G3. VOI beats RESET on at least 60% of pairs where both clear level 2 - the target no version has met.
    (My honest odds for G3: about 1 in 3.)
G4. lp85: median level-2 actions within 3 of TRANSFER.
G5. On our original agent too: VOI clears lf52 level 2 on at least 8 of 10 seeds and beats RESET on at least 60%
    of pairs.


## Step G results (added 2026-11-11; VOI, 10 seeds x 6 games, both agents; 0 level-1 pairing mismatches; 0 failed runs)
| agent | mode | level 2 cleared (of 60) | beat / lost vs RESET | share | p | geo-mean ratio | lf52 (of 10) |
|---|---|---|---|---|---|---|---|
| combined | TRANSFER | 54 | 34 / 19 | 64% | 0.03 | 0.99 | 5 |
| combined | SELECTIVE | 57 | 31 / 23 | 57% | 0.17 | 1.14 | 9 |
| combined | VOI | 54 | 30 / 22 | 58% | 0.17 | 1.03 | 9 |
| original | TRANSFER | 52 | 36 / 15 | 71% | 0.002 | 0.89 | 3 |
| original | SELECTIVE | 55 | 29 / 24 | 55% | 0.29 | 0.89 | 9 |
| original | VOI | 57 | 29 / 26 | 53% | 0.39 | 0.93 | 9 |

- G1 RIGHT: combined VOI clears lf52 level 2 on 9 of 10.
- G2 WRONG: 54 of 60, not >= 56 (cd82 only 5 of 10).
- G3 WRONG: beats RESET on 58% of pairs (p = 0.17), not >= 60%. The trade-off is not broken.
- G4 WRONG: lp85 costs a median 6 actions vs TRANSFER, not <= 3.
- G5 WRONG: on our original agent VOI fixes lf52 (9/10) and clears 57 of 60, but beats RESET on only 53% of pairs;
  lp85 costs 24 actions.

## What Step G shows
- VOI behaves almost exactly like SELECTIVE: it repairs lf52 and loses transfer's benefit. The reason is visible in
  its logs: it re-checked a median of 27-48 carried kinds per game on the combined agent (up to 282 on the original),
  i.e. nearly everything. Most carried kinds rest on few tries, so their plausible ranges are wide and almost always
  overlap something; "could the order be wrong?" is true for almost every rule.
- So uncertainty alone cannot pick out the rules worth checking. My implementation also left out how often a rule
  is used (how many choices it affects), which is the other half of "cost of being wrong" - a fair criticism of
  this test. Adding it would be tuned on the same 6 games where lf52 carries the story, which is exactly the
  overfitting risk the controlled game generator is meant to avoid.


# Step H: controlled game generator (design and predictions written 2026-11-11, before any run)
## Why
Steps C, F and G rest on 6 games, and the harmful-transfer story on one (lf52). A generator lets us set the cause
of harmful transfer ourselves and test it on hundreds of games. It complements the real games; it does not replace them.
## Games (same interface as the ARC toolkit, so the agent code runs unchanged)
- 64x64 frame, click-only, 2 levels. Objects are filled rectangles; an object's kind = colour + size (the agent's
  own notion of kind). A 4x4 indicator near the top-left cycles through 4 colours.
- Roles of kinds within a level:
  - KEY (2 objects): clicking one removes it; removing both wins the level.
  - DECOY (4 or 12 objects): every click advances the indicator (always "does something", never progresses).
  - HALF (3 objects): advances the indicator only when it shows one of 2 of its 4 colours (does something ~half the time).
  - INERT (3 objects): nothing.
- Level 1: KEY = kind A, DECOY = B, HALF = C, INERT = D. Level 2 depends on the condition (layout re-drawn):
  - STABLE: same roles (transfer should help).
  - PROMOTED-HALF: the key becomes C, the old half-decoy; A becomes inert. This is the lf52 pattern (a weakly
    effective kind becomes the key while many always-effective decoys are ranked above it).
  - PROMOTED-INERT: the key becomes D, which did nothing on level 1; A becomes inert.
  - NEW: the key is a kind E never seen on level 1; A becomes inert.
- Usage frequency: 4 or 12 decoy objects. 25 games per condition x decoy count = 200 games; positions, colours and
  sizes drawn from a seeded generator. Budget 3,000 actions per game.
- Agent: our original rule agent (no Rudakov tiers, so colours carry no built-in preference). Modes RESET, TRANSFER,
  SELECTIVE, VOI; agent seed = game index, so modes are paired action for action until level 1 is cleared.
- Measure: level-2 actions per game, paired against RESET; level-2 clears.
## Predictions
H1. STABLE: TRANSFER uses fewer level-2 actions than RESET on at least 70% of games.
H2. PROMOTED-HALF: TRANSFER uses more level-2 actions than RESET on at least 60% of games, and the harm is larger
    with 12 decoys than with 4 (median TRANSFER/RESET ratio higher).
H3. PROMOTED-INERT is the worst case for TRANSFER: its median ratio to RESET is the highest of the four conditions.
H4. NEW: TRANSFER is within +/-15% of RESET (median ratio 0.85-1.15): nothing carried over applies to the key.
H5. The trade-off reappears: SELECTIVE and VOI are within 15% of RESET in PROMOTED-HALF (they repair the harm) but
    lose most of TRANSFER's gain in STABLE (their median ratio to RESET is closer to 1 than TRANSFER's).


## Step H pilot (6 games, before the main run) and revised design (written 2026-11-11, before the main run)
Pilot: RESET vs TRANSFER on 6 generated games (stable x2, promoted_half x2, promoted_inert, new). TRANSFER needed
MORE level-2 actions in all 6, including both STABLE games (34 vs 6; 98 vs 57). Cause: the agent's statistic is
"did the click change the frame", not "did it make progress". Decoys change the frame on every click (rate ~1.0),
while the key is clicked only twice per level (rate 0.75), so carried knowledge ranks every decoy above the key -
the lf52 mechanism, present even when the rules do not change. With decoys in every game, the first design could
not show transfer helping at all, so it did not test what H1-H5 were about. Predictions H1-H5 above are withdrawn
unscored; they are replaced below. This is a design change informed by the pilot, and is reported as such.
Revised design: decoy count {0, 6} instead of {4, 12}; inert kind D gets 10 objects instead of 3 (most clicks in
real games do nothing, which is the knowledge transfer can usefully carry). Everything else unchanged.
Revised predictions:
H1'. STABLE, 0 decoys: TRANSFER uses fewer level-2 actions than RESET on at least 70% of games.
H2'. With 6 decoys, TRANSFER uses more level-2 actions than RESET on at least 60% of games, in every condition
     (decoy dominance; the pilot already pointed this way, so this one is weaker evidence).
H3'. PROMOTED_INERT, 0 decoys: TRANSFER uses more level-2 actions than RESET on at least 60% of games (the key was
     useless on level 1, so it is ranked last).
H4'. NEW, 0 decoys: median TRANSFER/RESET ratio between 0.8 and 1.2.
H5'. Re-checking: in the cells where TRANSFER hurts (median ratio > 1), SELECTIVE and VOI have a median ratio closer
     to 1 than TRANSFER's; in STABLE with 0 decoys their gain is smaller than TRANSFER's.

Correction to the revised design (found by the validation script, before the main run): with 0 decoys the old HALF rule
("advance the indicator only while it shows one of its first 2 colours") stops working after two clicks, because
nothing else moves the indicator (measured effect rate 0.14). HALF now advances the indicator on every second click
of the same object (a hidden per-object count), giving ~0.5 in every condition.

## Step H results (added 2026-11-11; 200 generated games, 25 per condition x decoy cell; 3,000-action budget)
Checks: 0 level-1 pairing mismatches across the 4 modes; every game cleared both levels in every mode; validation
script passed (determinism, solvable in 4 clicks, no overlaps, effect rates DECOY 1.0 / HALF 0.51 / INERT 0.0).

Level 2, each mode vs RESET (games where it needed more / fewer actions; median mode/RESET ratio):
| condition | decoys | RESET median actions | TRANSFER | SELECTIVE | VOI |
|---|---|---|---|---|---|
| stable | 0 | 7 | 0/25, 0.38 | 7/10, 1.00 | 8/11, 1.00 |
| stable | 6 | 34 | 21/4, 1.43 | 1/24, 0.21 | 1/24, 0.21 |
| promoted_half | 0 | 5 | 0/14, 0.80 | 19/2, 1.20 | 20/2, 1.20 |
| promoted_half | 6 | 33 | 23/2, 1.55 | 0/24, 0.18 | 0/24, 0.18 |
| promoted_inert | 0 | 6 | 25/0, 3.50 | 5/16, 0.80 | 5/17, 0.78 |
| promoted_inert | 6 | 34 | 25/0, 2.00 | 0/25, 0.19 | 0/25, 0.19 |
| new | 0 | 7 | 3/22, 0.57 | 21/1, 1.29 | 21/1, 1.29 |
| new | 6 | 35 | 3/22, 0.79 | 21/2, 1.08 | 23/0, 1.12 |

- H1' RIGHT: STABLE, 0 decoys: TRANSFER faster on 25 of 25 (median ratio 0.38).
- H2' WRONG: with 6 decoys TRANSFER is slower in STABLE (21/25), PROMOTED_HALF (23/25) and PROMOTED_INERT (25/25),
  but faster in NEW (22 of 25 faster).
- H3' RIGHT: PROMOTED_INERT, 0 decoys: TRANSFER slower on 25 of 25 (median ratio 3.5).
- H4' WRONG: NEW, 0 decoys: TRANSFER median ratio 0.57, not 0.8-1.2. A never-seen key gets the optimistic
  starting rank and is tried first, while carried knowledge rules out everything else.
- H5' WRONG as worded: re-checking did not end up "closer to 1" than TRANSFER where TRANSFER hurt - it went far past
  1 in the other direction (ratio ~0.2, faster than RESET on 24-25 of 25 games in every 6-decoy cell). Its second
  half held: in STABLE with 0 decoys re-checking gains nothing (1.00) while TRANSFER gains a lot (0.38).

## What Step H shows
1. Whether carried knowledge helps depends on how it ranks the progress-making kind. It helps when the key ranks
   high (stable or never-seen key, few decoys); it hurts when kinds that merely "do something" outrank it (decoys)
   or when the key did nothing before (promoted_inert). This is the lf52 mechanism, now reproduced on demand.
2. A surprise: re-checking thinly supported rules is not only a safety cost. The key is used up when it works, so it
   is always the thinly evidenced kind; re-checking thin rules first therefore means trying the key first. With
   decoys present that makes re-checking ~5x faster than starting fresh.
3. Why the real games did not show this: there, dozens of kinds rest on few tries (Step G re-checked 27-282 per game),
   so "thin" no longer singles out the key. The number of thinly supported kinds is the likely variable that decides
   whether re-checking pays - a testable prediction for the next step.
Limitations: the generated games are tiny (RESET needs 5-35 actions); 2 levels; one key kind per level; the pilot
changed the design (reported above).


# Step I: does re-checking stop paying as thinly tested irrelevant kinds multiply? (written 2026-11-11, before any run)
## Design
- Same generator; conditions STABLE and PROMOTED_HALF, 6 decoys (the cells where re-checking was ~5x faster).
- Added: K "noise" kinds, each a single INERT object (does nothing) on both levels, positions re-drawn per level.
  K in {0, 4, 8, 16}. Each noise kind gets only a try or two on level 1, so it is thinly supported - like the
  dozens of rarely clicked kinds in the real games.
- 25 games per condition x K = 200 games; modes RESET, TRANSFER, SELECTIVE, VOI; paired as before.
- Games with K = 0 are drawn exactly as in Step H (checked by re-running RESET on Step H's games).
## Predictions
I1. SELECTIVE's median level-2 ratio to RESET rises with K (0 < 4 < 8 < 16) in both conditions.
I2. At K = 16, SELECTIVE is faster than RESET on at most 60% of games in each condition (at K = 0: 24 of 25).
I3. TRANSFER stays slower than RESET (median ratio > 1) at every K in both conditions.
I4. VOI stays within 10% of SELECTIVE's median ratio at every K.


## Step I results (added 2026-11-11; 200 generated games, 25 per condition x k; checks: noise games validated,
## Step H games reproduce exactly under the extended generator, 0 pairing mismatches, every game cleared)
Level 2 vs RESET (games slower / faster than RESET; median ratio mode/RESET):
| condition | k | RESET median | TRANSFER | SELECTIVE | VOI |
|---|---|---|---|---|---|
| stable | 0 | 34 | 25/0, 1.47 | 3/22, 0.19 | 3/22, 0.19 |
| stable | 4 | 38 | 22/3, 1.32 | 1/24, 0.24 | 1/24, 0.24 |
| stable | 8 | 42 | 20/5, 1.19 | 0/25, 0.33 | 1/24, 0.33 |
| stable | 16 | 50 | 7/10, 1.00 | 1/24, 0.46 | 3/22, 0.46 |
| promoted_half | 0 | 33 | 24/1, 1.58 | 1/24, 0.18 | 1/24, 0.18 |
| promoted_half | 4 | 37 | 25/0, 1.41 | 0/25, 0.28 | 1/24, 0.28 |
| promoted_half | 8 | 41 | 24/1, 1.27 | 2/23, 0.34 | 2/23, 0.34 |
| promoted_half | 16 | 49 | 24/1, 1.06 | 4/21, 0.51 | 3/22, 0.51 |
- I1 RIGHT: SELECTIVE's ratio rises steadily with k in both conditions (0.19 -> 0.46; 0.18 -> 0.51).
- I2 WRONG: at k = 16 SELECTIVE is still faster on 24/25 and 21/25 games (predicted <= 60%).
- I3 WRONG: TRANSFER's harm also shrinks with k and is gone in STABLE at k = 16 (ratio 1.00, 7 slower / 10 faster).
- I4 RIGHT: VOI matches SELECTIVE in every cell.
## What Step I shows
- The mechanism behaves as explained: each thinly tested irrelevant kind dilutes "thin = key", and re-checking's
  advantage falls from ~5x to ~2x over k = 0-16. It has not reached break-even at 16; a straight-line extrapolation
  (not a measurement) puts the crossing somewhere around 40-50 kinds, the range the real games are in.
- Carried knowledge gains from the same noise: it knows the noise kinds do nothing, while RESET must try them, so
  TRANSFER's handicap from decoys shrinks as noise grows.
- Limit: the layout holds at most 42 objects, so k > 16 needs a denser grid to test directly.


# Step J: denser layout, up to 64 noise kinds, 1,000 games (written 2026-11-11, before any run)
## Design
- Dense layout: 6-cell slots in a 9 x 10 grid (90 positions, was 42), every kind 2-4 cells per side (was 2-5),
  so objects of the same colour still never touch. Everything else as in Step I (STABLE and PROMOTED_HALF,
  6 decoys, KEY 2, HALF 3, INERT 10, noise kinds 1 object each, INERT).
- k in {0, 16, 32, 48, 64}; 100 games per condition x k = 1,000 games (he suggested more games; they cost seconds).
- Modes RESET, TRANSFER, SELECTIVE, VOI; paired as before.
## Predictions
J1. SELECTIVE's median ratio to RESET rises with k (0 < 16 < 32 < 48 < 64) in both conditions.
J2. Break-even is reached: at k = 64 SELECTIVE's median ratio to RESET is >= 1.0 in both conditions.
J3. In STABLE, TRANSFER is faster than RESET (median ratio < 1) at k >= 32.
J4. Layout check: at k = 16 SELECTIVE's median ratio is within 0.1 of Step I's (0.46 stable, 0.51 promoted_half).


## Step J results (added 2026-11-11; 1,000 dense-layout games, 100 per condition x k; checks: dense games validated
## incl. a 1-cell gap around every object, Step H and I games reproduce exactly, 0 pairing mismatches, all cleared)
Level 2 vs RESET (games slower / faster; median ratio mode/RESET):
| condition | k | RESET median | TRANSFER | SELECTIVE | VOI |
|---|---|---|---|---|---|
| stable | 0 | 34 | 78/22, 1.45 | 6/88, 0.22 | 7/86, 0.22 |
| stable | 16 | 50 | 34/46, 1.00 | 2/96, 0.50 | 3/95, 0.50 |
| stable | 32 | 66 | 18/82, 0.76 | 7/92, 0.60 | 8/91, 0.60 |
| stable | 48 | 82 | 0/100, 0.60 | 12/86, 0.72 | 15/83, 0.72 |
| stable | 64 | 94 | 2/98, 0.55 | 8/91, 0.68 | 14/85, 0.74 |
| promoted_half | 0 | 33 | 95/5, 1.58 | 6/90, 0.21 | 8/88, 0.21 |
| promoted_half | 16 | 49 | 96/4, 1.06 | 3/97, 0.47 | 4/96, 0.47 |
| promoted_half | 32 | 65 | 12/88, 0.80 | 6/94, 0.55 | 6/94, 0.55 |
| promoted_half | 48 | 81 | 0/100, 0.64 | 13/87, 0.60 | 13/87, 0.60 |
| promoted_half | 64 | 93 | 2/98, 0.57 | 20/77, 0.72 | 16/83, 0.68 |
- J1 WRONG (narrowly): SELECTIVE's ratio rises with k in PROMOTED_HALF (0.21 -> 0.72) but dips in STABLE from k=48 to
  k=64 (0.72 -> 0.68).
- J2 WRONG: no break-even. At k = 64 SELECTIVE is still faster than RESET (0.68 / 0.72).
- J3 RIGHT: in STABLE, TRANSFER is faster than RESET at k >= 32 (0.76, 0.60, 0.55).
- J4 RIGHT: at k = 16 the dense layout gives 0.50 / 0.47 against Step I's 0.46 / 0.51.
## What Step J shows
- Re-checking never falls behind starting fresh here, but its edge shrinks from ~5x to ~1.4x as noise grows.
- The best strategy flips: from k ~ 32-48 onward, keeping knowledge (TRANSFER) beats re-checking, in both conditions -
  even when the key changed (PROMOTED_HALF), because knowing which of dozens of kinds do nothing outweighs the decoys.
- This matches the real games, which have dozens of kinds: there TRANSFER helped (Step C) and re-checking cost more
  than it gained (Steps C, F, G). The generator now reproduces both regimes and the switch between them.
- Next hypothesis it suggests (not yet tested): the key is thin AND does something; noise is thin and does nothing.
  Re-checking only thinly supported kinds that showed any effect should keep re-checking's gain at low noise and
  transfer's gain at high noise.


# Step K: re-check only thin rules that showed an effect (EFFTHIN) (predictions written 2026-11-11, before any run)
## Idea (from Step J)
The key is thinly supported AND does something; noise kinds are thinly supported and do nothing. EFFTHIN re-checks a
carried kind early on a new level only if it had fewer than 10 tries on earlier levels AND changed the frame at least
once. Thin kinds that never did anything are trusted (kept low). Contradicted rules are still dropped. Otherwise
identical to SELECTIVE, so it pairs with every earlier run.
## Runs
(a) the 1,000 dense generated games of Step J; (b) the 6 real games x 10 seeds on the combined agent and on our
original agent (as in Steps C, F, G).
## Predictions
K1. Generated games: EFFTHIN is faster than RESET on at least 85% of games in every condition x k cell.
K2. Generated games: in every cell EFFTHIN's median ratio to RESET is within 0.05 of the better of TRANSFER and
    SELECTIVE (it gets the best of both).
K3. Real games, combined agent: EFFTHIN beats RESET on at least 60% of pairs AND clears level 2 on at least 56 of 60
    game-seeds - the trade-off broken. (My honest odds: about 1 in 3.)
K4. Real games, combined agent: EFFTHIN clears lf52 level 2 on at least 8 of 10 seeds.
K5. Real games, original agent: EFFTHIN beats RESET on at least 60% of pairs and clears lf52 on at least 8 of 10.


## Step K results (added 2026-11-11)
### Generated games (1,000 dense games of Step J; 0 pairing mismatches; all cleared)
EFFTHIN median ratio to RESET 0.05-0.12 in every cell, faster on 97-100 of 100 games (TRANSFER 0.55-1.58,
SELECTIVE 0.21-0.72). Caveat, measured on the Step H set: the generator's key is by construction thin and effective.
Where the key did nothing on level 1 (promoted_inert) EFFTHIN is as slow as TRANSFER (ratio 2.0-3.57); for a
never-seen key it is middling (0.89).
- K1 RIGHT: faster than RESET on >= 85% of games in every dense cell (97-100%).
- K2 WRONG as worded: not "within 0.05 of the better of TRANSFER and SELECTIVE" - far better than both.
### Real games, 6 games x 10 seeds (0 pairing mismatches; 0 failed runs)
| agent | mode | level 2 cleared (of 60) | beat / lost vs RESET | share | p | geo-mean ratio | lf52 (of 10) | lp85 vs TRANSFER |
|---|---|---|---|---|---|---|---|---|
| original | RESET | 58 | - | - | - | 1.00 | 9 | |
| original | TRANSFER | 52 | 36 / 15 | 71% | 0.002 | 0.89 | 3 | |
| original | SELECTIVE | 55 | 29 / 24 | 55% | 0.29 | 0.89 | 9 | |
| original | EFFTHIN | 59 | 39 / 18 | 68% | 0.004 | 0.90 | 9 | +0 |
| combined | RESET | 58 | - | - | - | 1.00 | 9 | |
| combined | TRANSFER | 54 | 34 / 19 | 64% | 0.03 | 0.99 | 5 | |
| combined | EFFTHIN | 52 | 27 / 23 | 54% | 0.34 | 1.14 | 5 | +0 |
- K3 WRONG: on the combined agent EFFTHIN clears level 2 on 52 (not >= 56) and beats RESET on 54% (not >= 60%).
- K4 WRONG: combined lf52 5 of 10 (not >= 8) - no better than TRANSFER.
- K5 RIGHT: on our original agent EFFTHIN beats RESET on 68% of pairs (p = 0.004) and clears lf52 on 9 of 10. It
  also clears level 2 on 59 of 60 (RESET 58) and costs nothing on lp85. On this agent it is the first version to be
  both as safe as RESET and clearly better than it: the trade-off is broken here.
### Why the two agents differ (a diagnostic, partial)
On the combined agent, level 1 of lf52 is cleared in 28-125 actions (original: 61-246), so the 4x4 colour-14 kind -
the level-2 key - is often clicked only 1-3 times and on 5 of 10 seeds never changed the frame. EFFTHIN then trusts it
as useless, the same boundary the generator showed (promoted_inert). This explains 3 of the 5 combined failures
(seeds 1, 4, 5); seeds 0 and 6 failed although it had shown an effect, and seeds 2 and 7 succeeded although it had
not. The mechanism is only partly explained.
### Caution
Five re-check variants (SURPRISE, DROPONLY, SELECTIVE, VOI, EFFTHIN) have now been tried on the same 6 games. EFFTHIN's
success on one agent was predicted in advance (K5), but with this many tries it should be confirmed on fresh seeds
before it is claimed.


# Step L: confirmation of EFFTHIN on fresh seeds (predictions written 2026-11-11, before any run)
## Why
Five re-check variants have been tried on the same 6 games and seeds 0-9. EFFTHIN's success on our original agent
(Step K, K5) was predicted in advance, but needs confirming on data it has never seen.
## Design
Our original agent (no Rudakov tiers), the same 6 games, NEW seeds 10-19, 10,000 actions. Modes RESET, TRANSFER,
SELECTIVE, EFFTHIN; paired as before. Nothing in the agent or the analysis changes; the criteria are fixed here.
## Predictions (success = L1 and L2 and L3 all hold)
L1. EFFTHIN beats RESET on at least 60% of the pairs where both clear level 2.
L2. EFFTHIN clears level 2 on at least as many game-seeds as RESET minus 1.
L3. EFFTHIN clears lf52 level 2 on at least 8 of 10 seeds.
L4. TRANSFER's lf52 failure replicates: at most 5 of 10.
L5. EFFTHIN's lp85 level-2 cost vs TRANSFER is at most 3 actions (median).


## Step L results (added 2026-11-11; original agent, fresh seeds 10-19, 6 games; 0 pairing mismatches; 0 failed runs)
| mode | level 2 cleared (of 60) | beat / lost vs RESET | share | p | geo-mean ratio | lf52 (of 10) |
|---|---|---|---|---|---|---|
| RESET | 56 | - | - | - | 1.00 | 9 |
| TRANSFER | 55 | 38 / 14 | 73% | 0.001 | 0.85 | 5 |
| SELECTIVE | 53 | 25 / 25 | 50% | 0.56 | 0.91 | 7 |
| EFFTHIN | 57 | 32 / 22 | 59.3% | 0.11 | 0.92 | 10 |
- L1 WRONG (narrowly): EFFTHIN beats RESET on 59.3% of pairs (32 of 54), below the 60% bar set in advance; p = 0.11.
- L2 RIGHT: EFFTHIN clears level 2 on 57 (RESET 56).
- L3 RIGHT: EFFTHIN clears lf52 on 10 of 10.
- L4 RIGHT: TRANSFER clears lf52 on 5 of 10.
- L5 RIGHT: lp85 cost vs TRANSFER 0 actions.
Verdict by the pre-set criterion (L1, L2 and L3 all needed): NOT confirmed - L1 missed by one pair.
What did replicate on fresh seeds: EFFTHIN is at least as safe as RESET, repairs lf52 completely and costs nothing on
lp85. What did not: a clear speed advantage over RESET (Step K: 68%, p = 0.004; here 59%, p = 0.11). EFFTHIN loses
ground on cd82 (7/10 clears, median 7,157 actions vs RESET 8/10, 4,476).
Pooling seeds 0-19 gives 71 of 111 pairs (64%, p = 0.002), but seeds 0-9 are the ones the idea was developed on, so
the pooled figure is not a clean confirmation.
Also of note: TRANSFER was unusually strong on these seeds (73%, 55 clears) - the "fast but unsafe" side holds up.

