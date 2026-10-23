# v0.1.0-alpha.4 — first reconstruction preview

This is a GitHub **pre-release for WordPress maintenance engineers**, not a production deployment or WordPress.org release. Start by looking at and editing the three generated demonstration pages. Do not install the test bootstrap on an existing site.

## What you can see

Pages → company / services / contact → Edit opens **S3先行保存 — ページ編集** in an explicitly enrolled environment. Change plain paragraphs, title or slug, then click **S3へ保存して反映**. Completion shows the generation. An unresolved operation can be resumed with **同じ保存を再開**; conflicts require rereading the current state. The visible WordPress is a projection. The immutable generation and request-derived expected result Q are the reconstruction source.

## Which download

- `ozeki-wordpress-resilience-0.1.0-alpha.4.zip`: installable administration/status plugin. Upload through Plugins → Add New → Upload Plugin → Activate. It does **not** enroll pages or enable S3-first editing by activation alone.
- `owr-development-kit-0.1.0-alpha.4.zip`: opt-in editor/API, external S3 and signed reconstruction tools, lab, tests and documentation. This is required for the reconstruction preview. It is not a WordPress plugin ZIP; extract separately.
- `manifest.json` and `SHA256SUMS`: exact archive identities. Keep older archives/state; do not replace retained assets.

## First screen, without cloud credentials

Use a dedicated Linux/WSL host with Docker, Python 3, PHP 8.1+ (mysqli, GD), Composer and the dependencies in `requirements-dev.txt`. Extract the kit and run `composer install --no-dev`. Obtain the pinned WordPress/MariaDB images named in `lab/m1/images.env`, and a local `selenium/standalone-chrome` image with matching Chrome/ChromeDriver. The reproducible core runtime is pinned; the browser testing image is a test-infrastructure prerequisite.

From the extracted kit, run the following with absolute paths to the new and previous administration ZIPs and a NEW private output directory:

```sh
python3 tools/run-rbr-wordpress-zip-lab.py   --output /absolute/private/alpha4-demo   --vendor-cache /absolute/owr-development-kit/vendor   --plugin-zip /absolute/ozeki-wordpress-resilience-0.1.0-alpha.4.zip   --old-zip /absolute/previous-administration.zip   --keep-local-demo --demo-port 18714
```

This runs the installation/update and editor checks, then retains a loopback-only generated WordPress. Read the private `demo.json` URL to log in as the generated administrator. Never publish that token. Open Pages, then Edit on company, services or contact. This local screen uses a **persistent filesystem S3 protocol double**, clearly separate from the [actual experimental S3 evidence](../../evidence-public/rbr-request-q-live.json). It does not send mail, call production, or sign anything. Its only host listener is `127.0.0.1:18714`.

The test may already have changed the generated pages; they are demonstration data. To stop, use `docker stop <web> <db>` with the exact names in private `demo.json`; to resume use `docker start <db> <web>`. Keep that output directory and containers if preserving demonstration state. After deciding it is disposable, remove only those two named containers and that named Docker network. Do not delete production data or S3 history.

## Actual S3 and reconstruction path

The [protected editor contract](../spec/rbr-wordpress-editor.md), [save API](../spec/rbr-wordpress-save.md), [request-derived Q](../spec/rbr-request-q.md) and [generation inlet](../spec/rbr-generation-kit.md) specify explicit enrollment and storage configuration. A dedicated operator must configure fixed-version retained S3 storage and scoped credentials; there is no general production setup wizard in this release. No permanent second EC2 is required by this bounded architecture.

Use the actual applied save receipt with `expected_ref` and a request profile containing pinned R/E/C references with `rbr-generation-kit.py`. Do not supply manual Q or derive it from observation. The result stops at independent approval pending. A separate signing authority reviews the kit; the existing signature, pin, current-registry, revocation and expiry checks must pass before `rbr-approved-kit.py` reconstructs a private new WordPress. Public activation is a separate human decision and is not implemented here. Test signing helpers and credentials are not production key management.

## Scope and limits

Three already enrolled root pages; plain paragraphs, title and slug; existing enrolled images and relations. No general Gutenberg/posts/Markdown/new-media editing, automatic production enrollment, legacy journal migration, pending-operation abandonment, automatic signing, approval extension or republication. Other mutation routes and custom plugins are not production-qualified. A request-derived Q describes intent; it does not prove malware absence or replace approval. Retention/independent-trust requirements remain unchanged.

Updates must preserve operator-owned configuration, completed/pending journals, Q, S3 references, signatures and trust history. Older enrollments without frozen Q context are rejected rather than silently reset; keep their old code/state pending explicit migration. Administration ZIP updates do not by themselves migrate the external kit. This release demonstrates preserved Q-capable state, not automatic migration of every historical prototype.

## Evidence and review

Real experimental S3: three edited generations, 21 browser checks, fixed request Q, independent test signature, source/builder workspaces hidden, two new WordPress logical states matching Q. Separate signer account on one host and cached OCI images; not physical separation or cold-cache qualification. Regression: 75 RBR tests. Earlier shortened observation remains 68h28m24s with two gaps; it does not qualify this new path or constitute a 72-hour pass.

Final archive installation/update evidence is published as a separate Release attachment after the archives are frozen. Auxiliary JSON canonicalization, shell quoting and earlier browser startup issues belong to test infrastructure; they are not claims of product vulnerability or product success. Existing production and AWS permissions remain unchanged.

Local environment note: the first demo preparation exhausted Docker automatic address pools before WordPress started. The runner now checks existing Docker subnets and host routes, then selects an unused dedicated /28. It does not remove or alter existing networks.
