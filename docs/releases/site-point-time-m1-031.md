# Selected complete-site recovery point — 2026-10-25

Original implementation-stage record; the earlier site-retention-final ZIP remains unchanged. Subsequent browser acceptance and the new packaged candidate are recorded in [final ZIP acceptance](point-time-final-m1-031.md). No formal release.

The complete-site admin form selects a Checkpoint and inclusive confirmed-history end. `SiteSnapshot::restore(ref, replace, work, end)` reads only the requested subsequent records and verifies their referenced resources before destination replacement. A missing end, gap, bad resource or end before the Checkpoint is rejected. The result records Checkpoint, requested and applied boundaries. The existing three-argument caller remains latest-observed-tail compatible. No individual-asset recovery semantics, approval, scheduling or cleanup behavior changes.

## Environment and focused acceptance

Reused existing dm WordPress/DB containers and standard EC2-role S3 reads. Read-only inspection found existing Checkpoints through 0/8/14/21/33 and formal history through 70. Available host memory was about 472 MiB and disk free about 52 GiB. A separate `owrpit_20261025_` table namespace and `/tmp/owr-point-time-20261025/content` directory avoided replacing any existing site or member data. No new infrastructure, S3 objects, IAM policy or authentication helper. The original server/DB were not consulted by reconstruction.

All cases used the same existing Checkpoint through 33 and existing S3 originals:

| End | Verified state | Post records |
| --- | --- | --- |
| 33 | Checkpoint only; trial article 33 remains published | 24 |
| 37 | Trial article 33 is absent after confirmed deletion | 23 |
| 67 | Trial article 37 matches its earlier confirmed body and status | 23 |
| 68 | Trial article 37 matches its updated confirmed body and status; later 69/70 excluded | 23 |

Body hashes after destination URL relocation: end67 `40858b487fe83e133c9140a0a17aa1e1fd09cb07afa48264b3f44e0c30eab132`; end68 `a5a99f83ce274806f763e2d942196547190153b0d6044870673dbd744db4184e`. They differ as expected and individually match selected S3 originals. This is not a new full-plugin compatibility matrix.

The actual admin action with capability and nonce checks accepted end68 and recorded requested=actual=68; end32 with Checkpoint33 failed before content change. Generated admin HTML contains the selector, requested end and detailed JSON. These are PHP/admin-handler integration checks, not a new browser-click acceptance claim.

Focused memory-S3 contract checks cover update/deletion/Checkpoint-only boundaries, incompatible Checkpoint, missing end, history gap, missing resource, and ignoring corrupt later history. Existing result, Checkpoint and retention-preview contracts passed. Existing live-site probe was byte-identical before/after; S3 formal-history hash remained `042b47018628267d263335b6f70ba62e00acc4ae16b4fcae3544368b6416b265`. Mail calls were zero and WP-Cron execution disabled. No S3 deletion, mail delivery, periodic execution or publication occurred. Applying a historical deletion replaced records only inside the new disposable namespace.

## Corrections and limits

- Product implementation correction: the first real run exposed reuse of the new end-number variable by an existing file-path loop, corrupting the reported requested number. Renamed it to `targetThrough`; the restored boundary itself was correct. Corrected results were rechecked.
- Test harness corrections: loaded WordPress's admin template functions for CLI-rendered UI, and used a saved shell script to preserve loop arguments across PowerShell/WSL/SSH. The latter failed the whitelist before restoration. Original failed logs remain in local evidence.
- Environment: the existing live-probe duplicate `DISABLE_WP_CRON` warning is unrelated to the new product behavior.
- One formal record is not necessarily a whole user edit. Select the last confirmed record of the intended operation when multiple records are involved. Arbitrary theme/menu/configuration changes without adapter history still need a new trusted baseline. No partial recovery is inferred from missing records.
- Only isolated trial code was updated; shared source/recovery sites and the validated ZIP were not deployed or rebuilt. Local evidence: `release-readiness/point-time-20261025/` (private admin HTML is not included here).
