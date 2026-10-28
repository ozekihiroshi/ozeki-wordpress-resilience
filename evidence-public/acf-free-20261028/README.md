# ACF free integration evidence

Research trial: ACF free 6.8.10 / isolated WordPress 7.1.3, 2026-10-28. Standard editor saves of a dedicated post and page, real S3 fixed-version reads and history confirmation, then dm administration-screen recovery from Baseline through 0 plus records 1–10. No existing site content or previous S3 assets were changed.

[result.json](result.json) records the source/S3/destination comparison. Fifteen field types per owner matched, including field keys and ACF API output. Original retrieval used the product fixed-version readback and hash verification. Unsupported information stayed in originals and generated unapplied reasons. The result is a summary, not a raw AWS trace.

See [English scope](../../packages/markdown-m1/docs/acf-free.md) and [日本語の対応範囲](../../packages/markdown-m1/docs/acf-free-ja.md) for exact boundaries and separation from simulated failure tests. Local logs, login credentials and temporary browser entry points are not distributed. No screenshot containing temporary access material is included.

The PR is based on public main 6951978. Product changes port the research implementation; the new direct-access guard follows main conventions. Offline contract results are recorded in the PR. Real S3/browser testing was on the research build; the integrated main candidate was not deployed to either server. No new ZIP or release is produced.
