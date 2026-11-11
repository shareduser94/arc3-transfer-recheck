"""Why does EFFTHIN fix lf52 on our original agent but not on the combined one? Level-1 evidence about the
level-2 key kind (4x4 colour-14 objects) at the moment level 1 is cleared, per seed, for both agents."""
import logging
import arc_agi
from arc_agi import OperationMode
from arcengine import GameAction, GameState
import rule_agent as ra
logging.disable(logging.INFO)
arc = arc_agi.Arcade(operation_mode=OperationMode.OFFLINE)
gid = [e.game_id for e in arc.get_environments() if e.game_id.startswith("lf52")][0]
for hyb in (False, True):
    rows = []
    for seed in range(10):
        env = arc.make(gid, seed=0); fd = env.reset(); ag = ra.RuleAgent(seed, "transfer", hybrid=hyb); n = 0
        while n < 10000:
            fr = ra.last_frame(fd); a = ag.act(fd, fr)
            fd2 = env.step(GameAction.from_id(a[0]), data={"x": a[1], "y": a[2]} if a[0] == 6 else None); n += 1
            ag.observe(fr, a, ra.last_frame(fd2), fd2.state == GameState.GAME_OVER)
            if fd2.levels_completed >= 1:
                k = [kk for kk in ag.tried if kk[:2] == ("obj", 14) and kk[2:] == (4, 4)]
                t = sum(ag.tried[kk] for kk in k); c = sum(ag.changed[kk] for kk in k)
                rows.append(f"s{seed}: L1 in {n:4d} actions, 4x4 colour-14 tried {t:2d} changed {c:2d}")
                break
            if fd2.state == GameState.GAME_OVER: fd2 = env.reset()
            fd = fd2
    print("COMBINED" if hyb else "ORIGINAL"); print("\n".join("  " + r for r in rows))
