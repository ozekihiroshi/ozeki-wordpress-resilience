# WP-Members membership recovery

> **設計・検証資料（過去の版を含みます） / Technical and historical reference.** 現行の導入案内ではありません。Use the [current user guide](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide.md) / [現行導入ガイド](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/user-guide-ja.md) and [配布状況 / distribution status](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/blob/main/packages/markdown-m1/docs/wordpress-org-candidate.md).

WP-Members 3.5.8.1 core membership support uses the existing complete-site
snapshot, immutable S3 originals and formal history. It does not use a separate
worker, credential helper or email replay.

## Scope

- Standard subscriber accounts: login, email, display name, WordPress password
  hash and profile fields declared by WP-Members, including approval/confirmation.
- Core settings, registration field definitions, dialogs and terms of service.
- Per-page/post unrestricted, restricted and hidden metadata.
- Registration, profile/password changes, approval changes and member deletion
  recorded at successful request completion. Multiple writes to one asset in a
  request are coalesced into its final state.

Activate WP-Members and create a trusted complete initial snapshot first. Changes
then use the existing protection switch and Resume history action. Original
storage and formal history must both finish before a change is recoverable.
WordPress may already show a change whose S3 record remains pending; losing the
source before confirmation loses that last change, not the last confirmed state.

Use **Restore complete site**, with the recorded WP-Members version installed at
the destination. Individual text recovery does not import memberships. Checkpoints
carry membership state and are overlaid with later confirmed history. The source
database and source plugin process are not used by recovery.

Recovered users are mapped by source site and source ID. Existing destination
accounts with colliding login/email are rejected before import; administrators
and unrelated accounts are not overwritten. Repeated recovery updates only mapped
subscriber accounts. Deletion removes only an account previously imported from
that source. User tables and membership settings participate in the content
transaction. Import uses direct records and does not invoke registration,
password-reset or notification callbacks.

Password hashes (never plaintext passwords), email addresses and member fields
are sensitive S3 recovery data. Existing S3 access and retention controls apply.
Sessions, reset keys, application passwords and privileged capabilities are not
copied. Users log in again after recovery.

## Administrator access during setup and recovery

WP-Members moderated registration checks administrator activation at the standard
WordPress login screen too. Preserving an administrator account and password does
not, by itself, guarantee a fresh login.

1. At source setup, verify the designated administrator is activated when moderation
   is enabled. An existing browser session can conceal missing activation.
2. Before recovery, prepare the destination administrator independently of recovered
   subscribers. If the saved settings enable moderation, verify this administrator
   has WP-Members `active=1`. Resolve missing activation for this explicitly authorized
   account before replacing content; retain administrative server access in case
   web login is unavailable.
3. After recovery, authenticate again through standard `wp-login.php` and confirm
   `wp-admin/` access. A preserved session does not satisfy this check.
4. Keep moderation and other members' approval states unchanged. Do not bulk-activate
   members, bypass authentication, or reset passwords to solve missing activation.
   Check notification behavior before using activation tools; mail-disabled trials
   must retain their notification guard.

In the isolated 2026-10-24 trial, the combined-test fixture enabled moderation but
left its administrators unactivated. Recovery reproduced this setting; it did not
remove administrator activation metadata. Activating only the designated trial
administrator on each site allowed fresh browser login. Other members, content,
moderation settings and administrator credential rows passed before/after checks.
This corrected trial preparation, not product code or the verified ZIP. Automatic
administrator activation is not implemented; this remains an operator prerequisite.

## Limits

Administrator/editor/custom roles, multisite accounts, paid membership extensions,
membership products/subscriptions, external identity providers, CAPTCHA secrets,
mail templates/transports, uploaded profile files and arbitrary plugin metadata
are not covered. Core subscriber membership is the tested contract. Removing or
changing custom field definitions requires checking that selected historical
member fields still match the restored definitions. No concurrent-write guarantee
is added: process loss before request-end capture and simultaneous changes to one
member remain outside this adapter's guarantee. S3 retention is not erased by
deleting a WordPress member. No automatic publication or scheduling is added.

## Validation, 2026-10-24

Existing community/dm Docker services hosted separate WordPress table namespaces
and content directories. AWS SDK default EC2 role credentials were used with a
dedicated sub-prefix in the existing experiment bucket. No existing site, member,
IAM setting or S3 object was overwritten.

Confirmed: initial snapshot; complete member originals and ordered history;
injected storage failure excluded from history, frozen retry and duplicate retry;
Checkpoint plus later profile change; password authentication after recovery;
unapproved/deactivated account rejection; guest restricted/member allowed body;
destination administrator unchanged; collision and session-metadata rejection.
These are WordPress/plugin API tests, not browser registration-form acceptance.

The CLI harness initially omitted REMOTE_ADDR (warning only). A reactivation
assertion initially assumed WP-Members retained the previous password; its default
registration settings generate a new password on reapproval. The test now uses a
normal explicit password update before checking the recovered credential. These
are harness assumptions, distinct from the new product membership adapter.
