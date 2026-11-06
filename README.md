# P22: Equity Duration and Predictability

Replication and extension of Benjamin Golez and Peter Koudijs (2025), *Equity duration and predictability*, Journal of Financial Economics **172**, 104114. [Paper DOI](https://doi.org/10.1016/j.jfineco.2025.104114).

**Status: local Python baseline implemented.** Tables 1, 2, 4, 5, 6, 7 and Figures 1, 3 are generated from the authors’ Mendeley package. All 263 independently recomputed numeric table cells match published rounding; three Table 4 smoothing values remain explicitly labeled source constants. Updated data, raw-stock reconstruction, the final report and product extension remain future work. See [implementation and audit](REPLICATION.md).

## Team

Lauris Li (Yuting Li; Lauristt), Yiyao Wang (PriscillaWyy), Gary Miao (garymmmjw), Luke Zhu (1143051639Luke). Setup commits use Lauris Li; each teammate should use their own author identity for subsequent work.

## Clean-clone setup

Requires Git and [uv](https://docs.astral.sh/uv/). The project uses Python 3.12 and a committed lockfile. No WRDS credentials or MATLAB/LaTeX installation are needed for the supplied-data baseline.

```bash
git clone git@github.com:Lauristt/p22_golez_koudijs_2025.git
cd p22_golez_koudijs_2025
uv sync --frozen
uv run doit
```

The default task downloads missing pinned inputs, cleans them, estimates the assigned exhibits, validates them and writes `_output/replication/index.html`. A second run skips unchanged work. `uv run doit accept` checks published-value agreement; `uv run doit checks` tests numerical methods and dependency rebuilding. For continuous local rebuilding, run `uv run python src/watch_pipeline.py`. The separate ChartBook site builds with `uv run doit site`. Template example analyses are not executed.

This implementation is currently on the local `local/python-replication` branch; the cloud repository contains the earlier setup and cleanup only until explicitly published.

For pip users, `requirements.txt` is exported from `uv.lock`; use Python 3.12 and a virtual environment, install with `pip install -r requirements.txt`, then run `doit`. To update dependencies, update `pyproject.toml`, run `uv lock`, and regenerate requirements with `uv export --no-hashes --no-dev --format requirements-txt --output-file requirements.txt`.

## Assigned scope

| Exhibit | Paper page | Workstream |
|---|---:|---|
| Table 1 | 4 | Strip/market summary statistics |
| Table 2 | 5 | Strip/market predictive regressions |
| Table 4 | 7 | Historical summary statistics |
| Figure 1, both panels | 8 | Payout and dividend-price history |
| Table 5 | 9 | Historical predictive regressions |
| Table 6 | 10 | Portfolio summary statistics |
| Table 7 | 10 | Portfolio predictive regressions |
| Figure 3 | 11 | Combined ER/payout summary |

Tables 8 and 9 are excluded.

## Data and configuration

[Authors' package, version 1](https://data.mendeley.com/datasets/fp6fryn7h3/1) is the first benchmark. Additional sources: Benjamin Golez's dividend-strip series; Golez-Koudijs (2018) historical series; CRSP and Compustat via WRDS; Davis-Fama-French book equity from Kenneth French. The course permits CRSP S&P 500 returns in place of Datastream. Package ingestion is implemented and pinned by file hashes; WRDS pulls and recent-data updates are pending. Original inputs and outputs stay ignored locally because the package includes third-party data restrictions.

`src/settings.py` and optional ignored `.env` configure `DATA_DIR`, `OUTPUT_DIR`, `START_DATE`, `END_DATE`, and `WRDS_USERNAME`. See `.env.example`. The baseline ends in 2022; later update runs must report actual source coverage. Never commit `.env`, secrets, raw restricted data or the source paper.

## Pipeline and next steps

Retain `.cruft.json`: this project was generated using `cruft create https://github.com/backofficedev/cookiecutter_chartbook`. Use `uv run cruft check` before reviewing future template updates.

The implemented dependency graph is original files → cleaned Parquet → estimates → figures → validation/report → hash history. `config/replication.json` contains baseline settings; `config/published_benchmarks.json` supplies validation references only, never estimator inputs.

Next: reconstruct restricted raw-security portfolios, update the sample, recover the missing smoothing-estimation code, register approved outputs for publication, and develop the agreed extension. See [REPLICATION.md](REPLICATION.md) for the MATLAB-to-Python map and numerical conventions.

Future work should go through teammate-reviewed pull requests. Every member must author at least one merged PR and review a teammate's PR under the course rubric.

## Extension

**Not yet agreed with the instructor.** Candidate: a reproducible equity-duration research monitor comparing ER/EDG across windows and payout groups, with uncertainty, sensitivity controls and source coverage. Replace this section with the actual agreement after consultation; extending the endpoint alone is the update, not the extension.

## Site and CI

`uv run doit site` builds the initial ChartBook site. GitHub Actions runs tests and a documentation build on pushes and PRs. A separate manual Pages workflow deploys `docs/` after GitHub Settings > Pages > Source is set to GitHub Actions. The setup site contains no paper screenshots or restricted data. Publishing the initial site does not imply the replication is complete.

## Milestones

Consultation by November 13, 2026; final group meeting by December 11, 2026. The graded main-branch snapshot is 24 hours before the booked final meeting. Meetings are not booked by this setup.

[Assignment](https://finm-32800.github.io/FinalProject/potential_final_projects.html) | [Rubric](https://finm-32800.github.io/FinalProject/final_project_rubric.html)
