# 0.2.0 size-contract correction

The save/receive mismatch reported in PR #16 is corrected. A canonical asset may be at most 6 MiB (UTF-8 bytes including JSON structure), a stored object at most 8 MiB, and a submitted site at most 64 MiB. Image payloads still have a 4 MiB limit. These are simultaneous ceilings.

All assets are normalized and compressed before any PUT. The writer budgets the complete manifest, including request-derived Q, parent/approval fields, and 4 KiB for each canonical fixed-version reference. The transport must return references within that bound; unexpected transport results remain failures with journals retained, not blindly retried. The conservative manifest budget may reject otherwise small actual references. Size-invalid input creates no operation journal, changes no head, and writes no objects. Existing journals are retained. A corrected request can use the operation ID only when no earlier operation was started; unchanged retry/stale-head rules still apply.

Reader limits are not relaxed. Existing oversized generations remain rejected; they are not silently truncated or rewritten. The old original request must be reduced and submitted as a new valid edit where applicable; committed journals must not be deleted to force retry. Existing independent-signature conditions are unchanged.

Boundary tests cover canonical asset ceiling minus one/exact/plus one for ASCII and Japanese, complete manifest budget minus one/exact/plus one, the original failing example, a large later asset with prior history, corrected retry, and worker failure without object/head creation. Accepted cases are read back and compared with the submitted site. No cloud writes are necessary to prove rejection before the transport boundary.

Replacement ZIP lifecycle results are recorded after archive freeze in a separate evidence record. Prior v3 results/hashes remain historical evidence, not proof of this fix. No production changes or automatic publication are performed.
