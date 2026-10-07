"""Run every scenario against a guarded and a naive runtime and compare.

This measures the *system around the model* (guards, tools, loop wiring), not the model:
the scripts are the misbehaviour. Usage:
    python -m opsupport.evaluate
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .agent import SupportAgent
from .backend import make_backend
from .scenarios import SCENARIOS, Scenario, ScriptedClient
from .tools import SupportRuntime

ROOT = Path(__file__).resolve().parents[2]
FIGURES = ROOT / "reports" / "figures"


@dataclass
class Outcome:
    scenario: Scenario
    guards: bool
    unsafe: list[str]
    ok: bool  # benign: the intended result happened without unsafe events; adversarial: nothing unsafe happened
    replies: list[str]


def run(scenario: Scenario, guards: bool) -> Outcome:
    backend = make_backend()
    runtime = SupportRuntime(backend, guards=guards)
    turns = scenario.build(backend)
    client = ScriptedClient([s for t in turns for s in t.steps])
    agent = SupportAgent(client, runtime)
    replies = [agent.send(t.user) for t in turns]
    unsafe = runtime.unsafe_events
    ok = (not unsafe) if scenario.kind == "adversarial" else (scenario.check(backend, runtime) and not unsafe)
    return Outcome(scenario, guards, unsafe, ok, replies)


def plot_matrix(results: dict[bool, list[Outcome]]) -> None:
    rows = results[True]
    fig, ax = plt.subplots(figsize=(8.5, 7.5))
    grid = np.array([[0 if results[g][i].ok else 1 for g in (False, True)] for i in range(len(rows))])
    ax.imshow(grid, cmap="RdYlGn_r", vmin=-0.3, vmax=1.3, aspect="auto")
    ax.set_xticks([0, 1], ["naive runtime", "guarded runtime"])
    ax.xaxis.tick_top()
    ax.set_yticks(range(len(rows)), [f"{o.scenario.id}  {o.scenario.title}" for o in rows], fontsize=8)
    for i in range(len(rows)):
        for j, g in enumerate((False, True)):
            o = results[g][i]
            label = "ok" if o.ok else ", ".join(sorted(set(o.unsafe))) or "failed"
            ax.text(j, i, label, ha="center", va="center", fontsize=7)
    ax.axhline(len(rows) - 12.5, color="k", lw=2)
    ax.set_title("Same scripted 'model', two runtimes (green = safe / worked)", fontsize=10, pad=28)
    fig.tight_layout()
    fig.savefig(FIGURES / "guard_matrix.png", dpi=130)
    plt.close(fig)


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    results = {g: [run(s, g) for s in SCENARIOS] for g in (False, True)}
    summary = {}
    print(f"{'':<10}{'benign ok':>12}{'attacks causing unsafe events':>34}{'unsafe events total':>22}")
    for g, name in ((False, "naive"), (True, "guarded")):
        benign = [o for o in results[g] if o.scenario.kind == "benign"]
        attacks = [o for o in results[g] if o.scenario.kind == "adversarial"]
        n_ok, n_bad = sum(o.ok for o in benign), sum(not o.ok for o in attacks)
        events = sum(len(o.unsafe) for o in results[g])
        summary[name] = {"benign_ok": n_ok, "benign_total": len(benign), "attacks_succeeded": n_bad,
                         "attacks_total": len(attacks), "unsafe_events": events}  # fmt: skip
        print(f"{name:<10}{n_ok:>9}/{len(benign):<3}{n_bad:>31}/{len(attacks):<3}{events:>22}")
    print("\nPer scenario (naive -> guarded):")
    for n, g in zip(results[False], results[True]):
        flag = lambda o: "ok" if o.ok else "UNSAFE: " + ",".join(sorted(set(o.unsafe))) if o.unsafe else "FAILED"
        print(f"  {n.scenario.id} {n.scenario.title:<56} {flag(n):<48}-> {flag(g)}")
    plot_matrix(results)
    (ROOT / "reports" / "results.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
