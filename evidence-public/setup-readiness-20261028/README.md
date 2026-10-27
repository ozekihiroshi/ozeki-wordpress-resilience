# Setup readiness verification — 2026-10-28

Development source: 0.3.2-dev. This does not modify or replace the WordPress.org submission.

- Isolated, generated WordPress / MariaDB containers; synthetic S3 transport. No existing site or real AWS bucket was accessed. Test containers and network were removed afterward.
- Actual initial capture, fixed-version resource reads, protection enablement and a published post reaching formal history passed.
- Missing confirmation, premature protection, non-InnoDB tables, suspended versioning, connection failure and a changed destination produced guidance or rejected the action as appropriate.
- Recovery mode hides/rejects a new initial site capture. Existing configured installations retain service access.
- Japanese/English generated admin output checked; Chromium checked the English page at desktop/mobile widths, unchecked required confirmation, role selector, and Check storage through web PHP.
- `tests/setup-readiness.php` under `php -n` covered missing ZIP support, inactive Markdown dependency, pending saves, Japanese guidance and destination binding.
- `tests/setup-readiness-actions.php` passed for the final recovery-mode guard on both primary and supplementary initial capture.
- Existing `tests/gfs-admin.php` passed with explicit terms confirmation. Changed PHP files passed syntax checks; `git diff --check` passed.

Reproduce the isolated run with `python3 packages/markdown-m1/tests/setup-preflight.py /tmp/owr-setup-unique-path`. It uses the same Docker images and local SDK/Markdown fixture paths as the existing test harness. This is a local S3 simulation, not an AWS IAM or live-network acceptance test.

Submitted ZIP (unchanged): `ozeki-resilience-0.3.1.zip`, SHA-256 `537504d9b5be632a277c084ddfacf2a4f8a220498f940b6dde32c9e7bf650dbe`.
