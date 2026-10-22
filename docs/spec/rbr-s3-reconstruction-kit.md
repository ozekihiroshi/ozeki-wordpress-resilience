# Fixed-version S3 reconstruction kit (generated-data experiment)

Current follow-up: [independent approval entry](rbr-signed-kit.md) now gates the supported S3 workflow. The unsigned experiment below is historical evidence; its CLI fetch is disabled.

Prototype CLI development kit, no public activation or production migration. This extends [private WP reconstruction](rbr-wordpress-reconstruction-minimum.md) by archiving the actual runtime closure, instead of relying on previously cached image IDs alone.

## Stored closure

The existing `queue-s3-adapter.py` and EC2-role request-signing script supply authenticated conditional PUT and VersionId GET. The RBR wrapper restricts keys to a new `sites/isolated-queue-lab/sets/AWS-.../rbr-*` namespace within the existing experimental bucket. It executes the scoped authorization script transiently over the existing SSH connection; no remote file, IAM, bucket-policy or server configuration is changed. Writer and reader remain separate roles. No original production data or keys enter the kit.

The closure contains A's individual page/image/profile/relationship objects, R, E, D, C, independently authored Q, and the exact planner/executor/comparison/bootstrap-for-WP source files. References are rewritten bottom-up to real acknowledged S3 Version IDs; changed manifests are new objects, never edits to previous originals. The S3-first fixture's synthetic generation timestamps are fixture provenance; actual storage protection is evaluated from S3 response evidence, not from those fixture timestamps.

WordPress/PHP and MariaDB Docker-save archives are gzip-compressed and split into bounded 8 MiB objects. E's package descriptor binds image ID, archive hash/size and ordered fixed-version chunk references. The loader checks each chunk and the assembled archive before `docker load`. Theme source bytes and execution code are also retrieved from the kit, not the sender checkout. P is regenerated from fetched D; it is not copied from the sender.

The root manifest is stored last. A separately retained root receipt supplies its exact VersionId, size and SHA-256. This receipt plus an independently available authenticated reader and trusted downloader are the recovery starting inputs. The experiment does not claim that merely finding an S3 key establishes authenticity, or implement an independent signed approval system for this new kit. Existing Restore approval/revocation conditions are unchanged.

## Transfer and recovery gates

- Version-specific GET, exact version/size/hash, SSE-S3 and GOVERNANCE retention evidence are required. Retention must be at least 35 days from the S3 object modification time and still active at retrieval.
- The PUT journal distinguishes started/unknown from acknowledged. An unknown request blocks automatic resend. Acknowledged identical objects can be reused on a publisher resume. Nothing deletes retained objects or shortens retention.
- Fetch uses a fresh destination. Missing/corrupt closure, unsupported code paths, invalid retention or mismatched image archive blocks reconstruction. Code extraction has a fixed file allowlist; there is no arbitrary archive-path extraction for application source.
- A cold dedicated Docker daemon with a separate data root/socket demonstrates independence from existing image cache. It starts with zero images, loads only the downloaded archives, and uses fetched D/code. The source intake and publication workspaces are set aside; neither is mounted in either reconstructed target.
- Reconstructed targets have separate DBs/uploads/origins/IDs, no published host ports, no external default route, blocked mail/WP HTTP, disabled Cron and draft-only authenticated previews. Compare each actual DB/HTTP observation with Q. A pass never publishes the site.

## Commands and limits

`tools/rbr-s3-kit.py publish --source ... --work ... --execute-generated-lab` stores a generated `corporate-test` preparation made by `rbr-reconstruct-lab.py --prepare-only`. `fetch --receipt ... --work ... --execute-generated-lab` retrieves a closed kit and regenerates P. The transport bootstrap needs its two existing helper scripts, Python, PHP and an available reader identity/SSH path. Runtime loading requires Docker and adequate temporary disk/RAM. This is not a one-click installation wizard.

All transfer evidence is reported separately from logical reconstruction equality. The two products remain independent; Backup for S3 is not modified. The original closed observation campaign is not restarted. Retained experimental S3 storage incurs ordinary storage charges until lifecycle/operator cleanup after retention; this task neither changes lifecycle nor deletes those objects.

Remaining work: generic source enrollment, portable installation/role setup, production authorization and release gates, resumable partial WP application, general themes/forms/blocks, long-term runtime maintenance and a signed root/independent incident policy for the new kit. The tested old image versions are pinned test artifacts, not production security recommendations.

See [machine-readable evidence](../../evidence-public/rbr-s3-reconstruction-kit.json) and [Japanese summary](rbr-s3-reconstruction-kit-jp.md).

## Runtime-store compatibility found during this experiment

The first empty Docker 29 daemon defaulted to the containerd image store, whereas the publisher used the classic overlay2 store. Loading the same verified MariaDB archive exposed a different manifest identity (`aa69a626...`) rather than the stored classic image/config identity (`6ae88e35...`); the exact-ID gate rejected it before WordPress reconstruction. The experiment did not substitute that ID or weaken validation. A second **empty** dedicated daemon explicitly used classic overlay2 (`features.containerd-snapshotter=false`) and imported the very same downloaded archive. Existing host Docker configuration was not modified and no S3 object was resent.

This is both an observed deployment-environment difference and a current portability limitation: use the tested compatible image-store/architecture bootstrap; automatic cross-store identity translation/admission is not implemented. D/E's exact image-ID requirement detects the mismatch but does not yet express a full host-runtime compatibility profile. Do not claim arbitrary Docker hosts are supported. The first failed import is retained separately from successful reconstruction evidence.

## Recorded outcome

PASS: 75 objects / 412,585,057 bytes stored and retrieved by fixed versions; all retention/hash checks passed. Two fresh private WordPress instances matched independently authored Q and each other. Source intake/publication folders were renamed and mode 000 during recovery, then restored to mode 0700 after it ended; originals are retained under `.sealed` names. Both runtime archives were loaded into an initially empty independent Docker data root. Four observed container mount configurations referenced only fetched code/inputs (read-only). Temporary containers/daemons and two same-bridge forwarding rules were removed; S3 retained objects remain.

Additional environment/testing findings: the host forwarding policy blocked traffic between new dedicated bridge containers despite working DNS and DB startup. Rather than relax existing rules, two narrowly scoped same-bridge-only accepts were inserted on the local test host and removed afterwards. An attempted fully separate network namespace caused the installed Docker daemon to panic before startup; its root cause remains undetermined. This is retained as a failed environment/test-platform attempt, not a plugin failure or a passed test. The final deployment also used a separate containerd execution namespace and an observation monitor tolerant of container deletion races.

16 regression invocations passed (including 7 S3 guard cases and 9 comparison replay cases). No cloud re-upload was needed for the host/runtime corrections. Publication and independent security approval remain separate.
