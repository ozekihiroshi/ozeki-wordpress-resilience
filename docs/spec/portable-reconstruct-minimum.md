# Portable content and minimal Reconstruct specification

English primary | [日本語](portable-reconstruct-minimum-jp.md)

2026-10-22. **Research/design only. Not implemented, tested, or approved for production.** No live site, production DB, export, network crawl, restore, or configuration operation was performed. Findings combine official WordPress documentation and static inspection of existing project code. Actual extraction coverage of any particular site is UNKNOWN; no percentage or conversion fidelity has been measured.

## Objective and initial boundary

Rebuild a small business information site from independently understandable content when its WordPress application/control plane is unavailable or untrusted. Preserve information, not the old program or identical design. Initial output: a local static preview with no PHP, source JavaScript, forms, external fonts, trackers or network fetches. Public deployment and WordPress import are later work. Backup for S3 remains independent; no integration or feature absorption is implemented by this proposal.

Initial scope: one site/language, selected published standard pages/posts and their local JPEG/PNG images. Operator identifies home, company, services and contact information plus required pages/images. Complex blocks, builders, custom post types, commerce, membership, multilingual relations, comments, search, redirects, forms and API-driven functions are not automatically reconstructed. They are inventoried as dependencies. PDF and other formats may be preserved as restricted originals but are not automatically copied into the public output. A required PDF must receive a separately reviewed handling decision; it cannot disappear under a success label.

## Research basis

WordPress serializes block content into post_content; that representation is useful raw material, not a complete independent rendering specification. [Block data format](https://developer.wordpress.org/block-editor/explanations/architecture/data-flow/).

WXR exports content records but not site options or actual attachment files; export eligibility also depends on post-type export settings. Therefore WXR alone is not a standalone site package. [WP-CLI export](https://developer.wordpress.org/cli/commands/export/), [export_wp source and contract](https://developer.wordpress.org/reference/functions/export_wp/).

The standard page API describes parent, menu order, links, content and featured media; media records describe URLs, alternative text and media details. These help discover relations but do not prove that bytes have been copied or every use has been found. [Pages](https://developer.wordpress.org/rest-api/reference/pages/), [Media](https://developer.wordpress.org/rest-api/reference/media/).

Dynamic blocks generate content when rendered. Stored source alone can therefore be insufficient. [Dynamic blocks](https://developer.wordpress.org/block-editor/how-to-guides/block-tutorial/creating-dynamic-blocks/). The handling decisions below are this project's proposed design, not guarantees from these sources.

## Extractability and loss matrix

| Asset/relation | Independently preservable source | Minimum reconstruction | Loss or dependency to report |
|---|---|---|---|
| Classic HTML / basic static blocks | Exact stored body, title, excerpt, dates, source ID/URL | Paragraphs, headings, lists, emphasis, quotes, text/code and approved links/images | CSS/layout, inline styling and unsupported markup removed; per-node record |
| Tables | Original HTML/block attributes | Preserve as raw only in v1; show review-required placeholder | Cell merges/layout and business meaning cannot silently become plain text |
| Pages and posts | Stable package ID, type, status, slug, title, timestamps | Independent page with predictable path | Exact theme layout, archives and permalink behavior not promised |
| Parent/child and ordering | Parent ID and explicit order | Hierarchy plus operator-approved navigation | Page parent is not the same as menu membership |
| Navigation | Menu item IDs/targets/order or stored navigation references when available | Known page targets; otherwise generated hierarchy proposed for review | Theme locations, conditional/plugin menus, external or missing targets |
| Inline / featured images | Original binary, original URL, attachment ID, alt/caption, hashes | Validated JPEG/PNG derivative with local references | Crops, srcset selection, animation, metadata and theme backgrounds |
| Page links / anchors | Original href, source node, target ID/URL/fragment | Map enrolled site URLs and IDs to local pages; preserve resolvable anchors | Aliases/query URLs/fragments not resolvable with certainty remain issues |
| Categories/tags | IDs, names and membership | Retain metadata; archive generation deferred | Dynamic taxonomy views and search behavior |
| Reusable/synced blocks | Referenced content plus ID graph | Detect reference; v1 requires review, does not claim expansion | Missing references, cycles, revision mismatch, plugin rendering |
| Dynamic blocks / shortcodes | Stored attributes/text and declared dependency | Placeholder and optional manually approved replacement text | Output may require PHP, DB queries, plugin code or external service |
| Custom fields / builders / custom types | Explicitly selected raw records where obtainable | Inventory dependency; adapter needed later | Schema, hidden content, plugin tables and rendering not generically understood |
| Headers, footer, logo, contact details | Selected settings/template references and captured source, where accessible | Operator supplies/approves business identity and navigation | May be absent from page bodies or stored in widgets/theme/builder options |
| Forms, maps, video and embeds | Labels and source references | Remove active embed; approved textual alternative/link | Submission, map behavior, remote availability and external effects |
| PDF/SVG/other media | Restricted original plus type/hash | Not automatically published in v1 | Active features, parsers and document content need a separate policy |
| Users/secrets/site configuration | Excluded from portable public material | No old accounts, credentials, options or executables imported | Reconnection and new identities are separate setup tasks |

A preserved raw record is NOT a supported rendered feature. Count these separately. Unrecognized constructs must produce a location-specific issue, not be dropped or executed to discover their meaning.

## Acquisition design: two stages, no hidden source dependency

1. During normal authorized operation, enumerate selected published standard posts/pages, required metadata, references and image bytes. Include pagination/completeness checks. Do not export drafts/private/password-protected content, revisions, comments, users or all custom fields by default. Keep selected raw sources access-controlled: publicly rendered content can still contain private raw metadata.
2. On a controlled local process, parse the saved source as data, normalize supported nodes and build relations. Never load source PHP/theme/plugins, run shortcodes/render callbacks, deserialize objects, or execute imported SQL to convert it.

Initial preferred producer is an explicit structured export adapter plus local media copy; WXR can be retained as optional interoperability material, not the canonical portable format. REST can supply observations, but rendered content is not equivalent to raw source, and permissions/context/custom exposure affect coverage. Public crawling is at most a later visual comparison aid, not a completeness oracle. Do not crawl or fetch arbitrary URLs from content (SSRF, credentials and external side effects).

A WordPress-based exporter runs inside WordPress and may execute installed hooks; read-only intent does not make a compromised runtime trusted. It produces source observations, not proof of innocence. For incident response, prefer previously collected material or a separately designed offline extraction path; an SQL dump importer is NOT part of this minimum.

Consistency: record export start/end, selection, source revision/modified markers and file hashes. Detect changes during the window and mark unstable/partial; retain the attempt rather than replacing a complete generation. A revision marker alone cannot prove atomicity. Strong capture consistency can later reuse the existing capture contract where supported; v1 must not claim it without evidence. Never label an interrupted or missing-page export complete.

## Portable package proposal (new schema, not current Recovery Set)

- manifest.json: schema/version, package/site ID, time window, selected and required IDs, entry point, counts, checksums, consistency state, dependency/issue summaries, converter policy/version and provenance.
- raw/: exact selected content records and optional WXR; never web-served or copied to publication output.
- content/<id>.json: title, type, source identity/status, timestamps, parent/order, supported typed content nodes, media and link references. This is the canonical normalized content; raw HTML is not an executable node type.
- readable/<id>.md: human-readable derivative using a fixed Markdown subset, with links to local readable pages and included media. Raw HTML disabled. Unsupported constructs are labeled, not silently flattened. Markdown editing/re-import is outside v1.
- media/originals/: restricted original bytes named with safe IDs; index retains original human names and source URLs.
- media/derived/: dimension/byte-bounded JPEG/PNG decoded and re-encoded by maintained tooling, hashes and derivative provenance. This reduces risk, not proof of safety.
- relations.json: typed edges (parent, navigation, inline link, image, featured image) with original reference, resolved target and unresolved reason.
- issues.json plus plain-language report: per-page/node severity, preserved/converted/omitted/unknown status, fallback and operator decision. README explains package use without WordPress.

No filenames are trusted as paths; use bounded regular files, safe IDs, collision handling and traversal/symlink rejection. Block external XML entities, resource exhaustion and arbitrary YAML/object loading. Hashes bind bytes, not truth. Package reading requires neither the original domain nor the source DB; tools/dependencies and bootstrap trust/access requirements must be documented and available separately.

## Reconstruction and review rules

Generate HTML from typed allowlisted nodes into a fresh output directory using a packaged clean template/CSS. Escape text, reject active attributes/raw HTML and dangerous URL schemes; no JavaScript, iframe, form or automatic remote resources. Validate URI schemes and map internal references by origin/path/ID, not string substitution. Do not treat guid as the canonical public URL. Missing/ambiguous references remain visible; external hyperlinks require review but are never fetched during build. Email/telephone links are allowed only after explicit contact review.

States are separate: acquisition complete/partial/unstable; conversion supported/partial/blocked; preview built; operator reviewed; publication authorized. No state means malware-free. Required missing content or unresolved required dependencies blocks release readiness, not access to the salvaged readable material. Operator can explicitly remove a requirement or approve a documented substitute; it is never auto-waived.

Review only the scoped decisions: required business pages; conversion/dependency exceptions; company identity/contact details and important changes; final publication. Names, bank details and contact destinations may be maliciously changed even in harmless plain text. Compare important facts with an independent operator-approved reference where available; otherwise mark unverified and require review. Do not claim semantic truth from a checksum or clean template.

## Existing code versus new work

Static inspection: tools/first-site-capture.py validates scoped DB/file capture and archive/member hashes; tools/first-site-docker-lab.py enumerates attachment files; existing S3/signature/trust utilities protect immutable bytes and control use. These are reusable primitives, not a semantic export pipeline. No portable content normalizer, dependency-loss classifier, portable relationship graph or static reconstruct builder was found in the inspected tools/src scope. Existing generated-site restoration and its test passes do not validate this proposal. Reuse requires an explicit new asset/schema adapter; do not reinterpret old signatures as approval for reconstructed output.

Priority sequence: (1) read-only extraction inventory and required-page selection; (2) portable package, typed normalizer and exhaustive loss report; (3) offline static preview and reference checks; (4) important-information review and reproducible build evidence; (5) optional existing immutable storage integration. WordPress import, broad builder support and automatic deployment are deferred. Do not expand monitoring/systemd/VM machinery to implement this minimum.

## Future acceptance criteria, NOT executed now

Use one small generated corporate site with supported content plus deliberately unsupported shortcode/table/builder metadata, broken link and missing image. Demonstrate correct issue attribution rather than silently increasing conversion coverage. Require: every selected item accounted for; every required image and page present or explicit blocking issue; raw data retained separately; human-readable package; source/domain/DB unavailable during preview build; no secret/private content in output; no executing source code or external network calls; deterministic output for the same package/tool version; reviewed required business information present. Record preserved/converted/review-required/blocked counts by page, time and package size. Do not substitute a single overall success percentage or another full SQL restore test.

No new environment or test-infrastructure result exists in this research-only task. Product gaps above are missing capabilities, not failures inferred from an unrun test. Existing historical defects remain separate. Before testing a real site, separately agree the content scope and destination; no live export is authorized or performed here.
