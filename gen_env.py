"""Controlled mini-games for Step H, with the same interface as the ARC toolkit's offline environments,
so the rule agent and its runner play them unchanged.

Game id: "g<idx>-<condition>-<decoys>", e.g. "g007-promoted_half-6". (Pilot: decoys 4/12, 3 inert objects.) Everything is drawn from a seeded RNG.
Click-only, 2 levels, 64x64 frames, background colour 0. Object kinds = colour + size.
Roles: KEY (click removes it; remove all KEY objects to win the level), DECOY (click advances the indicator),
HALF (every second click on the same object advances the indicator; hidden per-object count), INERT (nothing).
Level 1: A=KEY, B=DECOY, C=HALF, D=INERT. Level 2 by condition:
  stable          A=KEY,  B=DECOY, C=HALF,  D=INERT
  promoted_half   C=KEY,  B=DECOY, A=INERT, D=INERT
  promoted_inert  D=KEY,  B=DECOY, C=HALF,  A=INERT
  new             E=KEY,  B=DECOY, C=HALF,  D=INERT, A=INERT   (E never appears on level 1)
"""
import random
import numpy as np
from arcengine import GameAction, GameState

CONDITIONS = ("stable", "promoted_half", "promoted_inert", "new")
IND_COLOURS = (11, 12, 13, 14)            # indicator colours, never used by objects
KIND_COLOURS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15)
N_KEY, N_HALF, N_INERT = 2, 3, 10        # N_INERT was 3 in the pilot
SLOT, ROWS, COLS, Y0, X0 = 9, 6, 7, 10, 1


class Frame:
    def __init__(self, grid, state, levels_completed, win_levels):
        self.frame = [grid.copy()]
        self.state = state
        self.levels_completed = levels_completed
        self.win_levels = win_levels
        self.available_actions = [6]


def parse(gid):
    """'g007-stable-6' or, for Step I, 'g007-stable-6-n8' (8 noise kinds). Returns idx, condition, decoys."""
    parts = gid.split("-")
    return int(parts[0][1:]), parts[1], int(parts[2])


def parse_noise(gid):
    for p in gid.split("-")[3:]:
        if p.startswith("n"):
            return int(p[1:])
    return 0


def is_dense(gid):
    return gid.endswith("-d")                    # Step J: 6-cell slots, 9 x 10 grid, kinds 2-4 cells per side


def level_roles(cond, level):
    if level == 0 or cond == "stable":
        return {"A": "KEY", "B": "DECOY", "C": "HALF", "D": "INERT"}
    if cond == "promoted_half":
        return {"C": "KEY", "B": "DECOY", "A": "INERT", "D": "INERT"}
    if cond == "promoted_inert":
        return {"D": "KEY", "B": "DECOY", "C": "HALF", "A": "INERT"}
    if cond == "new":
        return {"E": "KEY", "B": "DECOY", "C": "HALF", "D": "INERT", "A": "INERT"}
    raise ValueError(cond)


class GenEnv:
    def __init__(self, gid):
        self.gid = gid
        idx, cond, nd = parse(gid)
        assert cond in CONDITIONS
        self.rng = random.Random(f"{idx}-{cond}-{nd}")
        self.slot, self.rows, self.cols, smax = (6, 9, 10, 4) if is_dense(gid) else (SLOT, ROWS, COLS, 5)
        cols = self.rng.sample(KIND_COLOURS, 5)
        self.kinds = {}
        for name, c in zip("ABCDE", cols):
            self.kinds[name] = (c, self.rng.randint(2, smax), self.rng.randint(2, smax))   # colour, h, w
        self.counts = {"KEY": N_KEY, "DECOY": nd, "HALF": N_HALF, "INERT": N_INERT, "NOISE": 1}
        k = parse_noise(gid)                     # Step I: k extra kinds, one inert object each, on both levels
        noise = {}
        while len(noise) < k:
            cand = (self.rng.choice(KIND_COLOURS), self.rng.randint(2, smax), self.rng.randint(2, smax))
            if cand not in self.kinds.values() and cand not in noise.values():
                noise[f"N{len(noise)}"] = cand
        self.kinds.update(noise)
        roles = [dict(level_roles(cond, lv), **{n: "NOISE" for n in noise}) for lv in range(2)]
        self.levels = [self._layout(roles[lv]) for lv in range(2)]
        self.win_levels = 2
        self.level = 0
        self._load()

    def _layout(self, roles):
        slots = self.rng.sample([(r, c) for r in range(self.rows) for c in range(self.cols)], sum(
            (N_KEY if role == "KEY" else 2 if (role == "INERT" and name == "A") else self.counts[role])
            for name, role in roles.items()))
        objs, i = [], 0
        for name, role in roles.items():
            n = N_KEY if role == "KEY" else 2 if (role == "INERT" and name == "A") else self.counts[role]
            colour, h, w = self.kinds[name]
            for _ in range(n):
                r, c = slots[i]; i += 1
                y, x = Y0 + r * self.slot + 1, X0 + c * self.slot + 1
                objs.append({"kind": name, "role": role, "colour": colour, "y": y, "x": x, "h": h, "w": w, "alive": True})
        return objs

    def _load(self):
        self.objs = [dict(o) for o in self.levels[self.level]]
        self.ind = 0

    def _grid(self):
        g = np.zeros((64, 64), dtype=np.uint8)
        g[2:6, 2:6] = IND_COLOURS[self.ind]
        for o in self.objs:
            if o["alive"]:
                g[o["y"]:o["y"] + o["h"], o["x"]:o["x"] + o["w"]] = o["colour"]
        return g

    def _frame(self, state=GameState.NOT_FINISHED):
        return Frame(self._grid(), state, self.level, self.win_levels)

    def reset(self):
        self._load()
        return self._frame()

    def step(self, action, data=None):
        if action == GameAction.ACTION6 and data is not None:
            x, y = int(data["x"]), int(data["y"])
            for o in self.objs:
                if o["alive"] and o["y"] <= y < o["y"] + o["h"] and o["x"] <= x < o["x"] + o["w"]:
                    if o["role"] == "KEY":
                        o["alive"] = False
                    elif o["role"] == "DECOY":
                        self.ind = (self.ind + 1) % 4
                    elif o["role"] == "HALF":
                        o["hits"] = o.get("hits", 0) + 1     # every second click on this object does something
                        if o["hits"] % 2 == 1:
                            self.ind = (self.ind + 1) % 4
                    break
        if not any(o["alive"] and o["role"] == "KEY" for o in self.objs):
            self.level += 1
            if self.level >= self.win_levels:
                self.level = self.win_levels
                return Frame(self._grid(), GameState.WIN, self.level, self.win_levels)
            self._load()
        return self._frame()


class GenArcade:
    """Stand-in for arc_agi.Arcade: make(gid) returns a fresh game."""
    def make(self, gid, seed=0):
        return GenEnv(gid)


def game_ids_noise(n_per_cell=25, ks=(0, 4, 8, 16)):
    """Step I: STABLE and PROMOTED_HALF with 6 decoys, k noise kinds. k = 0 ids drop the suffix (same games as Step H's draw)."""
    out, idx = [], 1000
    for cond in ("stable", "promoted_half"):
        for k in ks:
            for _ in range(n_per_cell):
                out.append(f"g{idx:04d}-{cond}-6" + (f"-n{k}" if k else "")); idx += 1
    return out


def game_ids_dense(n_per_cell=100, ks=(0, 16, 32, 48, 64)):
    """Step J: dense layout, STABLE and PROMOTED_HALF with 6 decoys, k noise kinds, 100 games per cell."""
    out, idx = [], 2000
    for cond in ("stable", "promoted_half"):
        for k in ks:
            for _ in range(n_per_cell):
                out.append(f"g{idx:04d}-{cond}-6-n{k}-d"); idx += 1
    return out


def game_ids(n_per_cell=25, decoys=(0, 6)):      # pilot used (4, 12)
    out, idx = [], 0
    for cond in CONDITIONS:
        for nd in decoys:
            for _ in range(n_per_cell):
                out.append(f"g{idx:03d}-{cond}-{nd}"); idx += 1
    return out
