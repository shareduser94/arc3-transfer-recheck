"""Writes compare_f.py: compare_c6.py pointed at the combined agent's result files."""
t = open('compare_c6.py', encoding='utf-8').read()
reps = [('Step C analysis: 5 modes x 10 seeds on 6 games', 'Step F analysis (copy of compare_c6.py for the combined agent): 5 modes x 10 seeds on 6 games'),
        ('f"results/{m}_s{s}_c6.json"', 'f"results/hyb_{m}_s{s}_c6.json"'),
        ('for m in ("reset", "transfer", "surprise"):', 'for m in ("reset", "transfer"):'),
        ('f"results/{m}_s{s}.json"', 'f"results/hyb_{m}_s{s}.json"')]
for a, b in reps:
    assert t.count(a) == 1, a
    t = t.replace(a, b)
open('compare_f.py', 'x', encoding='utf-8').write(t)
print('compare_f.py written')
