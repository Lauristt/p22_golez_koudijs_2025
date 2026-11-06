# P22: Equity Duration and Predictability

Replication and extension of Benjamin Golez and Peter Koudijs (2025), *Equity duration and predictability*, Journal of Financial Economics **172**, 104114. [Paper DOI](https://doi.org/10.1016/j.jfineco.2025.104114).

**Status: initial setup.** The documentation pipeline runs, but the empirical replication, updated sample, validation exhibits, final LaTeX report and research product are not implemented yet.

## Team

Lauris Li (Yuting Li; Lauristt), Yiyao Wang (PriscillaWyy), Gary Miao (garymmmjw), Luke Zhu (1143051639Luke). Setup commits use Lauris Li; each teammate should use their own author identity for subsequent work.

## Clean-clone setup

Requires Git and [uv](https://docs.astral.sh/uv/). The project uses Python 3.12 and a committed lockfile. No WRDS credentials or LaTeX installation are needed for the initial documentation build.

```bash
git clone git@github.com:Lauristt/p22_golez_koudijs_2025.git
cd p22_golez_koudijs_2025
uv sync --frozen
uv run doit
```

The default task runs the scaffold tests and builds the ChartBook site in `docs/`. It does **not** execute the template's example analyses or claim replication results. The template example scripts/report files are retained only as development references.

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

[Authors' package, version 1](https://data.mendeley.com/datasets/fp6fryn7h3/1) is the first benchmark. Additional sources: Benjamin Golez's dividend-strip series; Golez-Koudijs (2018) historical series; CRSP and Compustat via WRDS; Davis-Fama-French book equity from Kenneth French. The course permits CRSP S&P 500 returns in place of Datastream. Actual package ingestion and WRDS pulls are pending; record source versions and licensing before redistribution.

`src/settings.py` and optional ignored `.env` configure `DATA_DIR`, `OUTPUT_DIR`, `START_DATE`, `END_DATE`, and `WRDS_USERNAME`. See `.env.example`. The baseline ends in 2022; later update runs must report actual source coverage. Never commit `.env`, secrets, raw restricted data or the source paper.

## Pipeline and next steps

Retain `.cruft.json`: this project was generated using `cruft create https://github.com/backofficedev/cookiecutter_chartbook`. Use `uv run cruft check` before reviewing future template updates.

1. Freeze exhibit specifications and tolerances before estimating results.
2. Add pull scripts, immutable raw inputs, and source manifests.
3. Add separate cleaning and analysis modules; parameterize time coverage.
4. Test source reconciliation, identities, filters and coverage; produce an original validation table and figure.
5. Replicate the eight exhibits, then update each to the latest available data.
6. Register real outputs and sources in `chartbook.toml`; add a cleaned-data tour notebook and generated LaTeX report.

Future work should go through teammate-reviewed pull requests. Every member must author at least one merged PR and review a teammate's PR under the course rubric.

## Extension

**Not yet agreed with the instructor.** Candidate: a reproducible equity-duration research monitor comparing ER/EDG across windows and payout groups, with uncertainty, sensitivity controls and source coverage. Replace this section with the actual agreement after consultation; extending the endpoint alone is the update, not the extension.

## Site and CI

`uv run doit site` builds the initial ChartBook site. GitHub Actions runs tests and a documentation build on pushes and PRs. A separate manual Pages workflow deploys `docs/` after GitHub Settings > Pages > Source is set to GitHub Actions. The setup site contains no paper screenshots or restricted data. Publishing the initial site does not imply the replication is complete.

## Milestones

Consultation by November 13, 2026; final group meeting by December 11, 2026. The graded main-branch snapshot is 24 hours before the booked final meeting. Meetings are not booked by this setup.

[Assignment](https://finm-32800.github.io/FinalProject/potential_final_projects.html) | [Rubric](https://finm-32800.github.io/FinalProject/final_project_rubric.html)
