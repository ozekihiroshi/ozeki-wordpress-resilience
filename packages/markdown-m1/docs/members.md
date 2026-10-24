# WP-Members membership recovery

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
