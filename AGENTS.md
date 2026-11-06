# Project conventions

Use the current contributor's own Git identity. For work performed for Lauris Li in this setup, the repository-local author and committer name is `Lauris Li`, with `156524798+Lauristt@users.noreply.github.com`. Do not append Codex, Claude, AI signatures, or assistant co-author trailers to commits or submissions. Do not overwrite teammates' identities.

Keep source PDFs, exhibit screenshots, restricted raw data, credentials, and `.env` out of all Git history. Commit scripts, provenance, and original explanatory prose. `.env.example` may contain placeholders only.

Run `uv run doit` for the project pipeline. The default pipeline builds the assigned baseline exhibits; three Table 4 smoothing cells are unrecomputed source constants. New replication work currently stays local. Never present original-paper screenshots or template examples as replicated results. Keep data ingestion, cleaning, analysis, and presentation separate as the project develops.

Future substantive work should use pull requests reviewed by a teammate. Preserve `.cruft.json` for template updates.
