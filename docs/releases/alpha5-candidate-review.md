# Alpha.5 candidate review — unpublished prototype

Based on merged PR #14 / main `751924d`. This change connects the protected editor generation and request-derived Q to an externally prepared and independently approved S3 kit, then exposes a reconstruction request and result in the WordPress administration console.

## Distribution identity

The validated archives remain frozen and are not rebuilt or published by this PR. All packaged runtime, tests and configuration examples match the reviewed source. README.md and RAADME-jp.md received post-validation results wording; this review and evidence-public/reconstruction-console-zip.json are post-freeze additions. Therefore a fresh archive built from the PR is not claimed byte-identical to these tested archives.

- `ozeki-wordpress-resilience-0.1.0-alpha.5.zip`: SHA-256 `30c156e853829aae87aa08a88f4c4cc6c6589f9a5b4c285b3dd5c539bef7c444`
- `owr-development-kit-0.1.0-alpha.5.zip`: SHA-256 `96de034c22c0af93046df2e812a1670a50a1eb6664b5e67112c38dff252a9c8b`

## Review and evidence

- Exact editor receipt, generation reference, Q binding and signed received kit are checked by the registration CLI. WordPress writes only a bounded identity/token request to the inbox; the worker owns configuration, trust, received kits and outcomes.
- Existing approved-kit verification/execution and root-owned current-trust checks are unchanged. No approval renewal, signing key in WordPress, automatic retry after interruption or public activation.
- Admin and enrolled-page capabilities, REST nonce, stale report refusal, local generation/Q match, exclusive queue creation, worker lock and persistent outcome journal bound the request path.
- `current-editor-reconstruction-console.json`: actual browser-edited generation on experimental S3, independently approved with a separate test account, fresh received kit, two disposable WordPress reconstructions matching request Q. Same-host signing does not prove physical host independence.
- `reconstruction-console-zip.json`: final ZIP fresh installation and alpha.4 plugin AND external-runtime upgrade; 24 browser checks, 18 lifecycle checks, 59 external files preserved, identical pending generation/Q resumed. 88 Python tests and PHP console contract passed. Signature/outcome preservation fixtures are not new cryptographic approval evidence. No additional S3 writes or signing were performed for ZIP testing.

## Remaining product limitations

Explicit external kit installation, AWS/retention configuration, enrollment, kit preparation, independent approval, registration and isolated worker setup remain necessary. Plugin activation alone does not protect edits. Three enrolled plain-text pages and existing image/relationship context only; ordinary Gutenberg/posts/media/Markdown authoring and generic Q-less legacy migration are unsupported. The console exposes the latest 20 local operations; older kits require operator handling. Long execution may age the report and disable new requests without implying execution failure. This worker is a generated-data disposable reconstruction entry, not production deployment. No permanent second EC2 is required by the architecture.

## Environment and test infrastructure

A WSL read-only polling connection timed out (`Wsl/Service/WSAETIMEDOUT`); the underlying trial completed and subsequent access recovered without restart or replay. Cause remains undetermined and is not classified as a plugin defect. Sandbox access denial required authorized execution, not WSL reconfiguration. Earlier browser-tool initialization and test-relay setup issues remain separately documented. No plugin fix is claimed for those issues.

日本語要約：未公開の試作候補です。実行コードは検証済みZIPと一致し、英日READMEの結果記載と別添評価のみ後から更新しています。署名・期限・失効条件は変更していません。WSL確認接続のタイムアウトは原因未確定の環境問題で、製品の対応範囲・未実装事項とは区別しています。本番変更・自動公開・正式リリースを含みません。
