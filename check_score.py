import json, logging
logging.disable(logging.INFO)
from arc_agi.scorecard import EnvironmentScoreCalculator
from agents import game_score
bad = 0; n = 0
import glob
for f in sorted(glob.glob("results/*_s[0-9].json")):
    for r in json.load(open(f)):
        r["score"] = game_score(r["level_actions"], r["baselines"])
        c = EnvironmentScoreCalculator()
        for i, b in enumerate(r["baselines"]):
            done = i < len(r["level_actions"])
            c.add_level(i + 1, done, r["level_actions"][i] if done else 0, b)
        off = c.to_score().score
        n += 1
        if abs(off - r["score"]) > 1e-9:
            bad += 1; print("MISMATCH", f, r["game"], off, r["score"])
print("checked", n, "mismatches", bad)
