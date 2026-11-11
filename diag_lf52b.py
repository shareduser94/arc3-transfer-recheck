"""lf52 level 2 over time: share of actions per kind per 1000-action bucket, masked effect rate, states."""
import logging, sys
from collections import Counter, defaultdict
import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction, GameState
import rule_agent as ra
logging.disable(logging.INFO)
arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
gid = [e.game_id for e in arc.get_environments() if e.game_id.startswith("lf52")][0]
for mode in ("transfer", "reset"):
    env = arc.make(gid, seed=0); fd = env.reset(); ag = ra.RuleAgent(0, mode)
    n = 0; lvl = 0; t2 = None; buckets = defaultdict(Counter); eff = defaultdict(Counter); newst = Counter(); seen = set()
    while n < 10000:
        fr = ra.last_frame(fd); s = ag.key(fr); a = ag.act(fd, fr)
        kind = ag.sig.get((s, a), ("act", a[0]))
        fd2 = env.step(GameAction.from_id(a[0]), data={"x": a[1], "y": a[2]} if a[0] == 6 else None); n += 1
        dead = fd2.state == GameState.GAME_OVER; fr2 = ra.last_frame(fd2)
        if lvl == 1:
            b = (n - t2) // 1000; buckets[b][kind] += 1
            s2 = ag.key(fr2); eff[kind]["n"] += 1; eff[kind]["chg"] += int(s2 != s)
            if s2 not in seen: seen.add(s2); newst[b] += 1
        ag.observe(fr, a, fr2, dead)
        if fd2.levels_completed > lvl:
            lvl = fd2.levels_completed; ag.new_level()
            if lvl == 1: t2 = n
            if lvl == 2: print(f"[{mode}] level 2 cleared after {n - t2} actions"); break
        if dead: fd2 = env.reset()
        fd = fd2
    print(f"[{mode}] level-2 masked effect rates: " + ", ".join(f"{k[1:]}:{v['chg']}/{v['n']}" for k, v in sorted(eff.items(), key=lambda kv: -kv[1]['n'])[:8]))
    for b in sorted(buckets):
        top = buckets[b].most_common(4)
        print(f"   bucket {b}: new states {newst[b]:4d} | " + ", ".join(f"{k[1:]}x{c}" for k, c in top))
