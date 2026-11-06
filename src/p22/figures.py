"""Render Figure 1 and a freshly linked Figure 3, plus the authors' frozen Figure 3."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .common import CLEAN, OUT, settings, write_json
from .econometrics import regression


def theme():
    """Use restrained publication styling at final output size."""
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelcolor": "#171717",
            "text.color": "#171717",
            "axes.edgecolor": "#5E6462",
            "axes.linewidth": 0.7,
            "legend.frameon": False,
            "savefig.facecolor": "white",
            "svg.fonttype": "none",
        }
    )


def save(fig, name):
    """Write vector and high-resolution previews from the same figure."""
    path = OUT / "figures"
    path.mkdir(parents=True, exist_ok=True)
    for ext in ["svg", "png"]:
        fig.savefig(path / f"{name}.{ext}", dpi=180)
    plt.close(fig)


def payout():
    """Translate Figure 1 values while correcting the MATLAB tick-year offset."""
    theme()
    cfg = settings()
    d = pd.read_parquet(CLEAN / "Data_US_1871_2022.parquet")
    d = d[d.Year.between(1871, cfg["baseline_end_year"])]
    h = cfg["rolling_years"]
    values = pd.DataFrame(
        {
            "year": d.Year,
            "payout": d.D_nom_WG.rolling(h).sum() / d.E_nom_WG.rolling(h).sum(),
            "dividend_price": (d.D_real / d.P_real).rolling(h).mean(),
        }
    ).iloc[h - 1 :]
    path = OUT / "figure_data"
    path.mkdir(parents=True, exist_ok=True)
    values.to_csv(path / "figure_1.csv", index=False)
    fig, axes = plt.subplots(2, 1, figsize=(7.0, 6.0), sharex=True)
    for ax, column, title in zip(
        axes,
        ["payout", "dividend_price"],
        [
            "A. Trailing 10-year dividend payout",
            "B. Trailing 10-year dividend-to-price ratio",
        ],
    ):
        ax.plot(values.year, values[column], color="#1F6F5F", linewidth=1.6)
        ax.set_title(title, loc="left", fontsize=11, pad=10)
        ax.set_ylabel("Ratio")
        ax.grid(axis="y", color="#E4E7E5", linewidth=0.5)
        ax.set_xlim(values.year.min(), values.year.max())
    axes[0].set_ylim(0.2, 0.9)
    axes[1].set_ylim(0, 0.08)
    axes[1].set_xlabel("Calendar year (trailing-window endpoint)")
    fig.subplots_adjust(left=0.12, right=0.97, top=0.94, bottom=0.14, hspace=0.42)
    fig.text(
        0.12,
        0.035,
        "Figure 1 • Author data; Python calculations. First complete window ends in 1880.\nPanel A uses nominal dividend/earnings sums; panel B averages annual D/P.",
        fontsize=8,
        color="#5E6462",
    )
    save(fig, "figure_1")


def summary():
    """Link Figure 3 to new tables; separately reproduce the saved-summary MATLAB plot."""
    theme()
    t4, t5, t6, t7 = [
        pd.read_csv(OUT / f"tables/table_{n}.csv", index_col=0) for n in [4, 5, 6, 7]
    ]
    data = []
    for source, px, er in [
        ("time", t4.loc["Payout (%)"], t5.loc["ER"]),
        ("cross", t6.loc["Payout (%)"], t7.loc["ER"]),
    ]:
        for label in px.index:
            data.append(
                {
                    "Payout": px[label],
                    "ER": er[label],
                    "Source": source,
                    "sample": label,
                }
            )
    fresh = pd.DataFrame(data)
    reference = pd.read_parquet(CLEAN / "author_summary.parquet")
    reference = reference[reference.Source.isin(["time", "cross"])].copy()
    path = OUT / "figure_data"
    path.mkdir(parents=True, exist_ok=True)
    fresh.to_csv(path / "figure_3.csv", index=False)
    reference.to_csv(path / "figure_3_author_summary.csv", index=False)
    for name, frame, label in [
        ("figure_3", fresh, "Recomputed from Tables 4–7"),
        (
            "figure_3_author_summary",
            reference,
            "Authors’ saved, rounded summary workbook",
        ),
    ]:
        fit = regression(frame.ER.to_numpy(), frame.Payout.to_numpy(), 0)
        fig, ax = plt.subplots(figsize=(7, 4.6))
        for group, marker, face, title in [
            ("time", "s", "none", "Time series"),
            ("cross", "o", "#171717", "Cross-section"),
        ]:
            g = frame[frame.Source == group]
            ax.scatter(
                g.Payout,
                g.ER,
                s=38,
                marker=marker,
                facecolors=face,
                edgecolors="#171717",
                label=title,
                zorder=3,
            )
        xx = np.linspace(frame.Payout.min(), frame.Payout.max(), 100)
        ax.plot(
            xx,
            fit.beta[0] + fit.beta[1] * xx,
            color="#5E6462",
            lw=1.3,
            label="Joint OLS fit",
        )
        ax.set(
            xlim=(30, 100),
            ylim=(0.2, 1.1),
            xlabel="Payout ratio (%)",
            ylabel="Expected-return share (ER)",
        )
        ax.set_title(
            "Figure 3. Higher payout is associated with lower ER",
            loc="left",
            fontsize=11,
            pad=14,
        )
        ax.legend(loc="upper right", fontsize=9)
        fig.subplots_adjust(left=0.12, right=0.96, top=0.87, bottom=0.24)
        fig.text(
            0.12,
            0.08,
            f"{label}. Joint fit R² = {fit.r2:.3f}.\nDescriptive association; no uncertainty intervals reported in the original figure.",
            fontsize=8,
            color="#5E6462",
        )
        save(fig, name)
        write_json(
            OUT / f"diagnostics/{name}.json",
            {
                "intercept": float(fit.beta[0]),
                "slope": float(fit.beta[1]),
                "r_squared": fit.r2,
                "nobs": fit.nobs,
                "source": label,
            },
        )
