"""Step A: RULE agent - graph exploration + counter mask + learned action-effect statistics.

Modes:
  reset    - everything learned (counter mask, effect statistics) is wiped at each new level
  transfer - learned knowledge is kept across levels
  surprise - kept across levels, but re-checked on each new level: each carried action kind is tried
             early, and its old evidence is dropped when this level's outcomes contradict it
             (log Bayes factor of "new evidence only" vs "old + new" > LBF_DROP); if most re-checked
             kinds are contradicted, all old evidence is dropped
  droponly - like surprise, but nothing is forcibly re-checked (contradictions are only noticed in passing)
  selective - like surprise, but only poorly established kinds (< N_CONF earlier tries) are re-checked
  voi       - like surprise, but a carried kind is re-checked only if its plausible range (mean +/- 2 sd) overlaps
              another kind's in the same state, i.e. their order could be wrong (value of information)
  effthin   - like selective, but only thin kinds that changed the frame at least once are re-checked; thin kinds
              that never did anything are trusted (Step K)
Within a level both modes learn in exactly the same way, so with the same seed the two runs are
identical until the first level is completed; every later difference comes from carried-over knowledge.

Usage: python rule_agent.py --mode transfer|reset --seed 0 --budget 10000 [--games ls20,ft09]
Writes results/<mode>_s<seed>.json
"""
import argparse, json, os, random, time, hashlib, logging, math
from collections import deque, defaultdict
import numpy as np
import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction, GameState
from agents import game_score, last_frame

logging.disable(logging.INFO)

TINY = 4          # a step changing 1..TINY pixels is a candidate counter tick
LINE_PX = 6       # distinct pixels a line needs before it is called a counter
LINE_SIGS = 2     # ...under at least this many different action kinds
MAX_LINES = 4
LINE_FREQ = 0.5   # ...and the line must change on at least this share of all steps (counters tick every step)
GOOD = 0.2        # an untried action is "worth walking to" above this predicted effect chance
VERIFY = 2        # SURPRISE: tries on a new level before carried knowledge about a kind is trusted
LBF_DROP = 2.0    # SURPRISE: log Bayes factor at which old evidence for a kind is rejected
N_CONF = 10       # SELECTIVE: kinds tried at least this often on earlier levels are trusted without re-check
SURPRISE_MODES = ("surprise", "droponly", "selective", "voi", "effthin")


def raw_key(fr):
    return hashlib.blake2b(fr.tobytes(), digest_size=12).digest()


def objects(fr, max_objs=80):
    """4-connected same-colour regions (background excluded): (size, x, y, type)."""
    vals, counts = np.unique(fr, return_counts=True)
    bg = vals[np.argmax(counts)]
    seen = fr == bg
    H, W = fr.shape
    out = []
    for y0 in range(H):
        for x0 in range(W):
            if seen[y0, x0]:
                continue
            c = int(fr[y0, x0])
            q = [(y0, x0)]; seen[y0, x0] = True; pix = []
            while q:
                y, x = q.pop(); pix.append((y, x))
                for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= yy < H and 0 <= xx < W and not seen[yy, xx] and fr[yy, xx] == c:
                        seen[yy, xx] = True; q.append((yy, xx))
            ys = [p[0] for p in pix]; xs = [p[1] for p in pix]
            pix.sort()
            y, x = pix[len(pix) // 2]
            otype = ("obj", c, max(ys) - min(ys) + 1, max(xs) - min(xs) + 1)
            out.append((len(pix), x, y, otype))
    out.sort(key=lambda o: o[0])                     # small objects first
    return out[:max_objs]


SALIENT = set(range(6, 16)); STATUS_COLOR = 16; MIN_W, MAX_W = 2, 32   # Rudakov et al.'s tier constants


def hybrid_objects(fr, smask=None, max_objs=80):
    """Like objects(), but status-bar cells (Rudakov mask) are recoloured 16 first, and each region gets
    Rudakov et al.'s salience tier (0 best .. 4 status bar). Sorted by tier, then size: (size, x, y, type, tier)."""
    vals, counts = np.unique(fr, return_counts=True)
    bg = vals[np.argmax(counts)]
    f = fr.astype(np.int16)
    if smask is not None:
        f = f.copy(); f[smask] = STATUS_COLOR
    seen = f == bg
    H, W = f.shape
    out = []
    for y0 in range(H):
        for x0 in range(W):
            if seen[y0, x0]:
                continue
            c = int(f[y0, x0])
            q = [(y0, x0)]; seen[y0, x0] = True; pix = []
            while q:
                y, x = q.pop(); pix.append((y, x))
                for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= yy < H and 0 <= xx < W and not seen[yy, xx] and f[yy, xx] == c:
                        seen[yy, xx] = True; q.append((yy, xx))
            ys = [p[0] for p in pix]; xs = [p[1] for p in pix]
            h, w = max(ys) - min(ys) + 1, max(xs) - min(xs) + 1
            sal, med = c in SALIENT, MIN_W <= h <= MAX_W and MIN_W <= w <= MAX_W
            tier = 0 if (sal and med) else 1 if med else 2 if sal else 4 if c == STATUS_COLOR else 3
            pix.sort()
            y, x = pix[len(pix) // 2]
            out.append((len(pix), x, y, ("obj", c, h, w), tier))
    out.sort(key=lambda o: (o[4], o[0]))
    return out[:max_objs]


class RuleAgent:
    def __init__(self, seed, mode, hybrid=False):
        self.hybrid = hybrid
        self.kind_tier = {}
        self._fp = None
        self.rng = random.Random(seed)
        self.mode = mode
        self.forget_knowledge()
        self.new_level(first=True)

    # ---------- knowledge that may transfer ----------
    def forget_knowledge(self):
        self.tried = defaultdict(int)     # action kind -> times tried
        self.changed = defaultdict(int)   # action kind -> times it changed the masked frame
        self.rows, self.cols = set(), set()
        self.row_px = defaultdict(set); self.row_sig = defaultdict(set)
        self.col_px = defaultdict(set); self.col_sig = defaultdict(set)
        self.steps = 0; self.row_steps = np.zeros(64, int); self.col_steps = np.zeros(64, int)
        self.mask_off = False             # set when the mask is suspected of hiding something
        # SURPRISE mode only: evidence from earlier levels, kept apart from this level's evidence
        self.old_tried = defaultdict(int); self.old_changed = defaultdict(int)
        self.lbf = defaultdict(float)     # kind -> log Bayes factor (new-only model vs old+new model)
        self.dropped = set()              # kinds whose old evidence was rejected on this level
        self.verified = set()             # carried kinds re-checked (>= VERIFY tries) on this level

    def _surprise_new_level(self):
        """Fold this level's evidence into the old evidence (dropped kinds lose their old part)."""
        for k in set(self.old_tried) | set(self.tried):
            keep = k not in self.dropped
            self.old_tried[k] = (self.old_tried[k] if keep else 0) + self.tried[k]
            self.old_changed[k] = (self.old_changed[k] if keep else 0) + self.changed[k]
        self.tried = defaultdict(int); self.changed = defaultdict(int)
        self.lbf = defaultdict(float); self.dropped = set(); self.verified = set()
        self.surprise_log.append(0)

    def _surprise_update(self, kind, y):
        on, oc = self.old_tried[kind], self.old_changed[kind]
        if on == 0 or kind in self.dropped:
            return
        n, c = self.tried[kind], self.changed[kind]
        pa = (oc + c + 1) / (on + n + 2)                 # old + new evidence
        pb = (c + 1) / (n + 2)                           # new evidence only
        self.lbf[kind] += math.log(pb if y else 1 - pb) - math.log(pa if y else 1 - pa)
        if n + 1 >= VERIFY:
            self.verified.add(kind)
        if self.lbf[kind] > LBF_DROP:
            self.dropped.add(kind); self.surprise_log[-1] += 1; self.surprise_events += 1
            if (len(self.verified) >= 4 and not self.level_switched
                    and len(self.dropped & self.verified) > 0.5 * len(self.verified)):
                self.dropped |= set(self.old_tried); self.level_switched = True; self.level_switches += 1

    # ---------- per-level search state ----------
    def reset_graph(self):
        self.adj = {}; self.untried = {}; self.sig = {}; self.dead = set()
        self.plan = deque(); self.obj_cache = {}

    def new_level(self, first=False):
        if first:
            self.surprise_log = [0]; self.surprise_events = 0; self.level_switches = 0; self.voi_rechecks = 0
        if not first and self.mode == "reset":
            self.forget_knowledge()
        if not first and self.mode in SURPRISE_MODES:
            self._surprise_new_level()
        self.level_switched = False
        self.mask_off = False
        self.status_mask = None; self.status_done = False   # HYBRID: Rudakov status-bar mask, per level
        self.recheck = set(); self.decided = set()           # VOI: carried kinds to re-check / already judged
        self.reset_graph()
        if first:
            self.fallbacks = 0; self.mask_events = 0; self.unmask_events = 0

    def _compute_status(self, fr):
        if self._fp is None:
            from rudakov_runner import heur              # their FrameProcessor, unmodified
            self._fp = heur.FrameProcessor()
        seg_map, segs = self._fp.segment_frame(fr)
        _, mask = self._fp.identify_status_bars(seg_map, segs)
        self.status_mask = mask.astype(bool) if mask.any() else None
        self.status_done = True

    def key(self, fr):
        sm = self.status_mask
        if not self.rows and not self.cols and sm is None:
            return raw_key(fr)
        m = fr.copy()
        if sm is not None: m[sm] = 0
        if self.rows: m[sorted(self.rows), :] = 0
        if self.cols: m[:, sorted(self.cols)] = 0
        return raw_key(m)

    def prio(self, kind):
        n, c = self.tried[kind], self.changed[kind]
        if self.mode in SURPRISE_MODES:
            on = self.old_tried.get(kind, 0)
            forced = (self.mode == "surprise" or (self.mode == "selective" and on < N_CONF)
                      or (self.mode == "voi" and kind in self.recheck)
                      or (self.mode == "effthin" and on < N_CONF and self.old_changed[kind] > 0))
            if on and forced and n < VERIFY:
                return 1.0                               # carried but not yet re-checked here
            if on and kind not in self.dropped:
                n += on; c += self.old_changed[kind]
        if n == 0:
            if self.hybrid:                              # unseen: start from Rudakov's salience tier
                return 1.0 - 0.1 * self.kind_tier.get(kind, 0)
            return 1.0                                   # optimism: unseen kinds first
        return (c + 1) / (n + 2)

    def _init_state(self, s, fd, fr):
        acts = []
        for a in fd.available_actions:
            if a in (0, 6):
                continue
            acts.append((a,)); self.sig[(s, (a,))] = ("act", a)
        if 6 in fd.available_actions:
            if s not in self.obj_cache:
                if self.hybrid:
                    self.obj_cache[s] = hybrid_objects(fr, self.status_mask)
                    for o in self.obj_cache[s]:
                        self.kind_tier[o[3]] = min(self.kind_tier.get(o[3], 4), o[4])
                else:
                    self.obj_cache[s] = objects(fr)
            for o in self.obj_cache[s]:
                x, y, ot = o[1], o[2], o[3]
                acts.append((6, x, y)); self.sig[(s, (6, x, y))] = ot
        self.rng.shuffle(acts)                           # random tie-break
        if self.mode == "voi":
            self._voi_decide([self.sig[(s, a)] for a in acts])
        self.untried[s] = acts
        self.adj[s] = {}

    def _estimate(self, kind):
        """(mean, sd) of a kind's chance of changing the frame, old (unless dropped) + new evidence.
        A kind with no evidence returns its fixed starting rank with sd 0."""
        n, c = self.tried[kind], self.changed[kind]
        on = self.old_tried.get(kind, 0)
        if on and kind not in self.dropped:
            n += on; c += self.old_changed[kind]
        if n == 0:
            return (1.0 - 0.1 * self.kind_tier.get(kind, 0) if self.hybrid else 1.0), 0.0
        m = (c + 1) / (n + 2)
        return m, math.sqrt(m * (1 - m) / (n + 3))

    def _voi_decide(self, kinds):
        """VOI: re-check a carried kind only if its order against another kind here could be wrong."""
        kinds = list(dict.fromkeys(kinds))              # unique, stable order
        est = {k: self._estimate(k) for k in kinds}
        for k in kinds:
            if k in self.decided or not self.old_tried.get(k, 0):
                continue
            self.decided.add(k)
            mk, sk = est[k]
            for j in kinds:
                if j == k:
                    continue
                mj, sj = est[j]
                if sk >= sj and abs(mk - mj) < 2 * sk + 2 * sj:
                    self.recheck.add(k); self.voi_rechecks += 1
                    break

    def _best_untried(self, s):
        acts = self.untried[s]
        i = max(range(len(acts)), key=lambda j: self.prio(self.sig[(s, acts[j])]))
        return acts.pop(i)

    def _has_good(self, u, thr):
        return any(self.prio(self.sig[(u, a)]) > thr for a in self.untried.get(u, ()))

    def _bfs(self, start, thr):
        prev = {start: None}; q = deque([start])
        while q:
            u = q.popleft()
            if u != start and self.untried.get(u) and self._has_good(u, thr):
                path = []
                while prev[u] is not None:
                    p, a = prev[u]; path.append((a, u)); u = p
                return list(reversed(path))
            for a, v in self.adj.get(u, {}).items():
                if v not in prev and (u, a) not in self.dead:
                    prev[v] = (u, a); q.append(v)
        return None

    def act(self, fd, fr):
        if self.hybrid and not self.status_done:
            self._compute_status(fr)
        s = self.key(fr)
        if s not in self.untried:
            self._init_state(s, fd, fr)
        if self._has_good(s, GOOD):                      # promising action right here
            self.plan.clear()
            return self._best_untried(s)
        if not self.plan:                                # walk to the nearest promising state
            path = self._bfs(s, GOOD)
            if path:
                self.plan.extend(path)
            elif self.untried[s]:                        # only likely no-ops anywhere: try one here
                return self._best_untried(s)
            else:
                path = self._bfs(s, -1.0)
                if path:
                    self.plan.extend(path)
        if self.plan:
            return self.plan[0][0]
        if (self.rows or self.cols or self.status_mask is not None) and not self.mask_off:
            # graph exhausted with no win: the mask may be hiding what matters -> drop it, re-explore
            self.rows, self.cols = set(), set(); self.mask_off = True; self.unmask_events += 1
            self.status_mask = None                      # HYBRID: drop the status-bar mask too (status_done stays True)
            self.reset_graph()
            return self.act(fd, fr)
        self.fallbacks += 1
        a = self.rng.choice([x for x in fd.available_actions if x != 0])
        return (6, self.rng.randrange(64), self.rng.randrange(64)) if a == 6 else (a,)

    def _update_mask(self, fr, fr2, kind):
        diff = fr != fr2
        self.steps += 1
        self.row_steps += diff.any(axis=1); self.col_steps += diff.any(axis=0)
        if self.mask_off:
            return False
        d = np.argwhere(diff)
        if not (0 < len(d) <= TINY) or len(self.rows) + len(self.cols) >= MAX_LINES:
            return False
        new = False
        freq_ok = lambda cnt: self.steps >= 10 and cnt >= LINE_FREQ * self.steps
        for r, c in d.tolist():
            self.row_px[r].add(c); self.row_sig[r].add(kind)
            self.col_px[c].add(r); self.col_sig[c].add(kind)
            if (r not in self.rows and len(self.row_px[r]) >= LINE_PX and len(self.row_sig[r]) >= LINE_SIGS
                    and freq_ok(self.row_steps[r])):
                self.rows.add(r); new = True
            elif (c not in self.cols and len(self.col_px[c]) >= LINE_PX and len(self.col_sig[c]) >= LINE_SIGS
                    and freq_ok(self.col_steps[c])):
                self.cols.add(c); new = True
        return new

    def observe(self, fr, a, fr2, dead):
        s = self.key(fr)
        kind = self.sig.get((s, a), ("act", a[0]) if a[0] != 6 else ("bg",))
        if self._update_mask(fr, fr2, kind):
            self.mask_events += 1
            self.reset_graph()                           # state keys changed: rebuild the graph
            return
        s2 = self.key(fr2)
        if self.mode in SURPRISE_MODES:
            self._surprise_update(kind, (not dead) and s2 != s)
        self.tried[kind] += 1
        if not dead and s2 != s:
            self.changed[kind] += 1
        if dead:
            self.dead.add((s, a)); self.plan.clear(); return
        if s in self.adj:
            self.adj[s][a] = s2
        if self.plan:
            pa, exp = self.plan.popleft()
            if pa != a or exp != s2:
                self.plan.clear()


def run_game(arc, gid, agent, budget, baselines):
    env = arc.make(gid, seed=0)
    fd = env.reset()
    win_levels = fd.win_levels
    level_actions, since, best, n, overs = [], 0, fd.levels_completed, 0, 0
    raw_states, states = set(), set()
    states_per_level, raw_per_level, actions_per_level_end = [], [], []
    t0 = time.time()
    while n < budget:
        fr = last_frame(fd)
        raw_states.add(raw_key(fr)); states.add(agent.key(fr))
        a = agent.act(fd, fr)
        fd2 = env.step(GameAction.from_id(a[0]), data={"x": a[1], "y": a[2]} if a[0] == 6 else None)
        n += 1; since += 1
        if fd2 is None:
            break
        dead = fd2.state == GameState.GAME_OVER
        agent.observe(fr, a, last_frame(fd2), dead)
        if fd2.levels_completed > best:
            for _ in range(fd2.levels_completed - best):
                level_actions.append(since); since = 0
            best = fd2.levels_completed
            states_per_level.append(len(states)); raw_per_level.append(len(raw_states))
            states, raw_states = set(), set()
            actions_per_level_end.append(n)
            agent.new_level()
        if fd2.state == GameState.WIN:
            break
        if dead:
            overs += 1
            fd2 = env.reset()
        fd = fd2
    states_per_level.append(len(states)); raw_per_level.append(len(raw_states))
    return {
        "game": gid, "win_levels": win_levels, "levels": best,
        "level_actions": level_actions, "baselines": baselines,
        "score": game_score(level_actions, baselines),
        "actions": n, "game_overs": overs,
        "states_per_level": states_per_level, "raw_states_per_level": raw_per_level,
        "level_end_at": actions_per_level_end,
        "mask_rows": sorted(agent.rows), "mask_cols": sorted(agent.cols),
        "mask_events": agent.mask_events, "unmask_events": agent.unmask_events, "fallbacks": agent.fallbacks,
        "surprise_per_level": agent.surprise_log, "level_switches": agent.level_switches, "voi_rechecks": agent.voi_rechecks,
        "secs": round(time.time() - t0, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["reset", "transfer", "surprise", "droponly", "selective", "voi", "effthin"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--budget", type=int, default=10000)
    ap.add_argument("--games", default="")
    ap.add_argument("--tag", default="")
    ap.add_argument("--hybrid", action="store_true", help="add Rudakov et al.'s status-bar mask and salience tiers")
    args = ap.parse_args()
    arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
    infos = {e.game_id: e for e in arc.get_environments()}
    gids = sorted(infos) if not args.games else [g for g in sorted(infos) if g.split("-")[0] in args.games.split(",")]
    os.makedirs("results", exist_ok=True)
    out = f"results/{'hyb_' if args.hybrid else ''}{args.mode}_s{args.seed}{args.tag}.json"
    res = []
    for gid in gids:
        meta = json.load(open(os.path.join(infos[gid].local_dir, "metadata.json")))
        agent = RuleAgent(args.seed, args.mode, hybrid=args.hybrid)
        r = run_game(arc, gid, agent, args.budget, meta["baseline_actions"])
        res.append(r)
        print(f"{gid} levels {r['levels']}/{r['win_levels']} score {r['score']:.3f} "
              f"level_actions {r['level_actions']} overs {r['game_overs']} "
              f"states {r['states_per_level'][-1]} raw {r['raw_states_per_level'][-1]} "
              f"mask r{r['mask_rows']} c{r['mask_cols']} unmask {r['unmask_events']} fb {r['fallbacks']} {r['secs']}s", flush=True)
        json.dump(res, open(out, "w"), indent=1)
    print("MEAN SCORE", round(sum(r["score"] for r in res) / len(res), 4),
          "games with >=1 level", sum(r["levels"] > 0 for r in res), flush=True)


if __name__ == "__main__":
    main()
