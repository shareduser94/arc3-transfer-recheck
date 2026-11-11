import json, glob, statistics as st
d = {}
for f in glob.glob("results/*_s[0-9].json"):
    agent = f.replace("\\", "/").split("/")[-1].split("_s")[0]
    for r in json.load(open(f)):
        for i, a in enumerate(r["level_actions"]):
            d.setdefault(agent, []).append(a / r["baselines"][i])
for k, v in d.items():
    print(k, "solved levels", len(v), "median actions/human", round(st.median(v), 1),
          "min", round(min(v), 2), "within 3x human", sum(x <= 3 for x in v))
