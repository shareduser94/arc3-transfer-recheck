"""Diagnose lf52: what does each mode know at level 2, and what does it spend actions on?"""
import json, os, logging, sys
from collections import Counter
import numpy as np
import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction, GameState
import rule_agent as ra
logging.disable(logging.INFO)

GAME = sys.argv[1] if len(sys.argv) > 1 else "lf52"
BUDGET = int(sys.argv[2]) if len(sys.argv) > 2 else 6000
arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
infos = {e.game_id: e for e in arc.get_environments()}
gid = [g for g in infos if g.startswith(GAME)][0]

def fmt(agent):
    rows = []
    for k in sorted(agent.tried, key=lambda k: -agent.tried[k]):
        rows.append(f"{k}: {agent.changed[k]}/{agent.tried[k]} p={agent.prio(k):.2f}")
    return rows

for mode in ("transfer", "reset"):
    env = arc.make(gid, seed=0); fd = env.reset()
    ag = ra.RuleAgent(0, mode); n = 0; lvl = fd.levels_completed
    l2 = Counter(); l2chg = Counter(); snap = None
    while n < BUDGET:
        fr = ra.last_frame(fd); a = ag.act(fd, fr)
        kind = ag.sig.get((ag.key(fr), a), ("act", a[0]))
        fd2 = env.step(GameAction.from_id(a[0]), data={"x": a[1], "y": a[2]} if a[0] == 6 else None); n += 1
        dead = fd2.state == GameState.GAME_OVER
        ag.observe(fr, a, ra.last_frame(fd2), dead)
        if lvl == 1:
            l2[kind] += 1; l2chg[kind] += int((fr != ra.last_frame(fd2)).any())
        if fd2.levels_completed > lvl:
            if lvl == 0:
                snap = fmt(ag); print(f"[{mode}] level 1 done at {n}; knowledge carried:" if mode == "transfer" else f"[{mode}] level 1 done at {n}")
                for r in snap[:12]: print("   ", r)
            lvl = fd2.levels_completed; ag.new_level()
            if lvl >= 2: print(f"[{mode}] level 2 done at {n}"); break
        if dead: fd2 = env.reset()
        fd = fd2
    print(f"[{mode}] level-2 action kinds used (count, raw-changed):")
    for k, c in l2.most_common(10): print(f"    {k}: {c} ({l2chg[k]})")
    print(f"[{mode}] mask rows {sorted(ag.rows)} cols {sorted(ag.cols)} unmask {ag.unmask_events} fallbacks {ag.fallbacks} states {len(ag.untried)}")
