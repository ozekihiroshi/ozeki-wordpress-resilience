# Synthetic WordPress scenarios for core daily updates

These PHP fixtures reproduce the defects found on 2026-11-24. They are development
tools, not plugin distribution files. They refuse sites whose URL does not start
with `http://owr-hypothesis-`.

Run only inside disposable WordPress containers, with an isolated database,
outgoing mail disabled, external HTTP blocked and the S3 client replaced by the
existing test transport. Do not use production credentials. Each process loads
`/var/www/html/wp-load.php` and reads/writes synthetic fixture files under `/lab`.

Use three separately prepared sites: source, first recovery and second recovery.
Install the same product source in each. Call `prepare` on the source, then the
operation modes below in separate PHP processes (so WordPress shutdown hooks
complete). After each operation, call `state`, `restore` on the first destination,
and `state` there. Compare values, not destination-local author IDs. Exclude the
default WordPress privacy-policy content from the lifecycle comparison because
the existing recovery presentation rules deliberately normalize its HTML.

| Fixture | Operation modes |
|---|---|
| properties.php | author, excerpt, discussion, parent, order |
| lifecycle.php | private, password, trash, untrash, password-clear, delete, recreate |
| taxonomy.php | tag-name, tag-slug, tag-description, ancestor-name, ancestor-parent, delete-tag, delete-child |
| options.php | front-page, site-title, timezone, reading |

Then call `resave` on the first destination, `state`, `restore-second` on the
second destination, and `state`. This uses a different synthetic prefix and
compares the result of a real WordPress edit after recovery. Hash all prior test
objects before doing this and assert that none change. Also run the lifecycle
fixture stopping after `password` so the second recovery must still require a
password for anonymous access.

Additional focused checks:

- Deny formal-history PUT for `front-page`. Assert queue > 0 and formal history
  remains at 0. Restore transport availability, call `resume` on the source and
  compare recovery. Existing original bytes, including empty files, must remain
  unchanged.
- After restoring the `trash` point, call `untrash` on that destination with
  protection disabled. Compare its comments and article state with the source's
  ordinary `untrash` result. This tests use of the restored metadata, not just its
  existence.

The bounded CI contracts are `core-update-contract.php`, `core-update-format.php`
and the existing editor/queue tests. `core-update-old-reader.php` consumes the JSON
fixture emitted by `core-update-format.php`; run it in a separate PHP process
against an extracted, unchanged rc.21 package. It must reject all three new
formats while still reading the legacy control original. No AWS access is needed.
