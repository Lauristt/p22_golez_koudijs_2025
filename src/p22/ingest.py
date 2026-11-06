"""Read author Excel files into typed, tidy Parquet inputs without estimating results."""

import numpy as np
import pandas as pd

from .common import CLEAN, RAW

GROUP_FILES = {
    "strips": ["Golez_Jackwerth_1996_2022.xls"],
    "history": [
        "Data_Netherlands_UK_1602_1812.xls",
        "Data_UK_1813_1870.xls",
        "Data_US_1871_2022.xls",
        "Dividends_Earnings.xls",
    ],
    "portfolios": ["Portfolios_Cross_Section.xlsx"],
    "summary": ["Data_Summary.xlsx"],
}
PORTFOLIOS = ["All", "Low", "Medium", "High", "Below 0.5", "Above 0.5"]


def validate_years(frame):
    """Require unique ascending annual observations before any lag construction."""
    years = frame["Year"].to_numpy(dtype=int)
    if len(years) != len(set(years)) or not np.all(np.diff(years) == 1):
        raise ValueError("Annual observations must be unique, ordered and contiguous")


def ingest(group):
    """Preserve source units and dates; normalize only labels and table structure."""
    CLEAN.mkdir(parents=True, exist_ok=True)
    for name in GROUP_FILES[group]:
        path = RAW / name
        if group == "portfolios":
            raw = pd.read_excel(path, header=1)
            validate_years(raw)
            frames = []
            for i, label in enumerate(PORTFOLIOS):
                block = raw.iloc[:, 1 + 8 * i : 9 + 8 * i].copy()
                block.columns = [
                    "n_stocks",
                    "dp",
                    "dividends",
                    "earnings",
                    "dg",
                    "eg",
                    "ret",
                    "retx",
                ]
                block.insert(0, "year", raw.iloc[:, 0].astype(int))
                block.insert(1, "portfolio", label)
                frames.append(block)
            tidy = pd.concat(frames, ignore_index=True)
            tidy.to_parquet(CLEAN / "portfolios.parquet", index=False)
        elif group == "strips":
            frame = pd.read_excel(path)
            frame["Date"] = pd.to_datetime(frame["Date"])
            periods = frame["Date"].dt.to_period("M")
            if periods.duplicated().any() or not np.all(
                np.diff(periods.astype("int64")) == 1
            ):
                raise ValueError(
                    "Strip inputs must contain one observation per consecutive month"
                )
            frame.to_parquet(CLEAN / "strips.parquet", index=False)
        elif group == "history":
            frame = pd.read_excel(path)
            validate_years(frame)
            frame.to_parquet(CLEAN / (PathStem(name) + ".parquet"), index=False)
        else:
            pd.read_excel(path).to_parquet(
                CLEAN / "author_summary.parquet", index=False
            )


def PathStem(name):
    """Retain authors' filenames for traceable historical series."""
    return name.rsplit(".", 1)[0]
