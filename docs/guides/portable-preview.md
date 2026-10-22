# Local static Reconstruct preview

English primary | [日本語](portable-preview-jp.md)

`tools/portable-preview.py --package PACKAGE --output NEW_DIRECTORY [--image-runtime sha256:PIN]` builds a review-only static preview from the previous portable package. It never boots WordPress, reads a source DB, fetches content URLs or publishes. The original package is unchanged. Existing output directories and source/output overlap are refused. Incomplete packages, unsafe paths, symlinks and checksum/size mismatches are rejected. Package checksums establish internal consistency, not authenticity or absence of compromise.

Output: index.html, page-ID.html, local style.css, successfully normalized media-ID.png and build.json. No raw source, SQL, old PHP/JS, source settings or private credentials are copied. Every page has a review banner, navigation to extracted pages and local/global issues. The index lists selected-but-unexported IDs. Structured text is escaped; only fixed allowed tags are emitted; no scripts, forms, embeds or external resource URLs. CSP further limits resources to local images/styles. Unresolved and external links are displayed as inert review items. Contact information remains text for human checking, not automatic mail/telephone actions.

New extractions preserve HTML id locations as ordered anchor nodes immediately before the original element. Preview links map decoded fragments to unique local anchor IDs. Duplicate targets and older packages without position nodes fall back to the page with an explicit position-not-preserved notice; suppressed active elements are never recreated as targets. Unsupported table/shortcode text may remain readable, but its issues remain prominent and it is never executed or described as a recreated function.

Images require an explicit pinned runtime. The existing cached PHP/GD image runs only a CLI decoder in a separate container with no network, read-only root, non-root UID, dropped capabilities and memory/PID bounds; no WordPress process, DB or source mounts are used. Input <=8 MiB, dimensions <=4096, pixels <=4 million. Valid PNG/JPEG is decoded and emitted as a new PNG, without copying source metadata. Decode failures are placeholders. This is a risk-reducing transformation, not proof of harmlessness; absent normalization configuration withholds images.

The supplied earlier generated 1x1 PNG has a bad IDAT CRC. GD recognized dimensions but refused decoding. The earlier extraction correctly preserved its bytes; hashing had never established image validity. The preview retains the source package unchanged and withholds that image. A separate newly generated valid PNG exercises successful normalization; it does not replace or repair the original fixture silently.

The first browser inspection could not read cssRules from a local-file stylesheet (SecurityError); the test now checks computed style instead. Original logs/screenshots are retained. This is a browser-test method issue, not an unexplained production environment fault.

Static generation does not authorize publication. Company/contact truth, missing functions, unresolved content and the known limits of source extraction still require review. No general-site deployment UI, new approval policy, S3 integration or automatic publication is added.

## Acceptance — 2026-10-22

7 unit tests and 6 Chromium checks passed. All three saved pages render with local navigation, missing/unsupported notices and no horizontal overflow at 390px. Browser used network none and no published port; the source WordPress containers were absent. All source package hashes remained unchanged. The 16 extraction issues plus 5 preview limitations are visible (21 total). Original fixture image withheld; separate valid PNG normalization passed. Output is a review preview, not publication readiness. [Evidence](../../evidence-public/portable-preview.json).

A second browser-only attempt also failed because the shared WebDriver helper treats dictionaries with an error key as failed WebDriver responses. Returning a scalar for that inspection corrected the harness; the third browser run passed. Both earlier logs/screenshots were preserved. No product checks were relaxed.

## Valid-image end-to-end follow-up

A new generated corporate fixture uses a valid 480×240 PNG generated with GD. Extraction, source-container removal, and package-only preview generation are exercised in sequence. The prior broken-image package and evidence remain unchanged. The new preview shows three pages, one normalized image and 18 review issues, including missing media/pages, unsupported forms/blocks and metadata. Anchor navigation retains the original heading position. This validates the supported subset, not arbitrary themes, layout fidelity or absence of compromise. See [roundtrip evidence](../../evidence-public/portable-roundtrip.json).
