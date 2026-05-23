"""One-off generator for the demo's plot submissions.

Run locally (your dev machine — Cloud Run doesn't carry matplotlib) to refresh
the PNGs under backend/demo_assets/. seed_demo.py reads them at seed time.

    python backend/demo_assets/generate_plots.py
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))


def _spectrum(seed: int):
    rng = np.random.default_rng(seed)
    background = rng.uniform(100.0, 150.0, size=450)
    signal = rng.normal(loc=125.0, scale=1.5, size=80)
    return np.concatenate([background, signal])


def _save(fig, name: str) -> None:
    out = os.path.join(HERE, name)
    fig.savefig(out, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    print(f"wrote {out} ({os.path.getsize(out) // 1024} KB)")


def amelia_clean() -> None:
    m = _spectrum(1)
    bin_edges = np.arange(100, 151)
    counts, _ = np.histogram(m, bins=bin_edges)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(bin_edges[:-1], counts, width=1.0, align="edge", edgecolor="white")
    ax.axvline(125.5, color="crimson", linestyle="--", label="peak at 125 GeV")
    ax.set_xlabel(r"$m_{\gamma\gamma}$  [GeV]")
    ax.set_ylabel("events / GeV")
    ax.set_title("Diphoton invariant mass spectrum")
    ax.legend()
    _save(fig, "higgs_amelia.png")


def priya_minimal() -> None:
    m = _spectrum(2)
    bin_edges = np.arange(100, 151)
    counts, _ = np.histogram(m, bins=bin_edges)
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    ax.step(bin_edges[:-1], counts, where="post", color="#2563eb")
    ax.fill_between(bin_edges[:-1], counts, step="post", alpha=0.18, color="#2563eb")
    ax.set_xlabel("m_gg (GeV)")
    ax.set_ylabel("events")
    ax.grid(True, alpha=0.25)
    _save(fig, "higgs_priya.png")


def henrik_dense() -> None:
    m = _spectrum(3)
    bin_edges = np.arange(100, 151, 0.5)  # finer binning
    counts, _ = np.histogram(m, bins=bin_edges)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(bin_edges[:-1], counts, width=0.5, align="edge", color="#0f766e", edgecolor="#0f172a", linewidth=0.3)
    peak_idx = int(np.argmax(counts))
    peak_x = bin_edges[peak_idx]
    ax.axvline(peak_x + 0.25, color="orange", linestyle=":", linewidth=2,
               label=f"argmax bin ≈ {peak_x:.1f}")
    ax.set_xlabel(r"$m_{\gamma\gamma}$  [GeV]")
    ax.set_ylabel("events / 0.5 GeV")
    ax.set_title("Higgs candidate — fine-binned spectrum")
    ax.legend()
    _save(fig, "higgs_henrik.png")


def yuki_offset() -> None:
    # A student who plotted but found 124, not 125 — to show the dashboard surfacing
    # near-miss attempts. Same data, different binning choice.
    m = _spectrum(5)
    bin_edges = np.arange(99.5, 150.5)  # offset by 0.5
    counts, _ = np.histogram(m, bins=bin_edges)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(bin_edges[:-1] + 0.5, counts, width=1.0, color="#7c3aed", edgecolor="white")
    peak_x = bin_edges[int(np.argmax(counts))] + 0.5
    ax.axvline(peak_x, color="black", linestyle="--", alpha=0.5)
    ax.text(peak_x + 0.6, max(counts) * 0.9, f"peak: {int(peak_x)} GeV", fontsize=9)
    ax.set_xlabel("invariant mass (GeV)")
    ax.set_ylabel("events")
    ax.set_title("γγ mass — peak finder")
    _save(fig, "higgs_yuki.png")


def main() -> None:
    amelia_clean()
    priya_minimal()
    henrik_dense()
    yuki_offset()


if __name__ == "__main__":
    main()
