# Terms of use

[日本語](terms-of-use-ja.md) · [README](../README.md) · [Setup and recovery guide](user-guide.md)

Updated October 28, 2026. Applies to Ozeki Resilience 0.3.3.

This document summarizes operational roles and the license provisions on warranty and liability. The [README coverage table](../README.md#what-remains-and-what-you-can-recover) describes what the product preserves and restores.

## 1. License

The software is provided under **GPL-2.0-or-later**. Rights and conditions for use, copying, modification and redistribution are governed by [LICENSE](../LICENSE). This document is not an additional agreement restricting GPL rights and does not replace the license. Bundled libraries retain their respective licenses.

## 2. Setup and operation

Use the product with sites and storage you are authorized to manage. The administrator prepares WordPress and AWS, selects content to protect, creates the initial capture and checks that saving has completed. See the [user guide](user-guide.md) for requirements and procedures.

Users prepare destination administrator access, external service connections and protection for assets outside the product's scope. Select a recovery point and inspect the restored content before making the destination public. The administrator also selects retention and cleanup settings.

## 3. Stored data and external services

The product sends data to the Amazon S3 storage you specify. In addition to articles and images, this can include personal data in inquiries and membership records, depending on the features used. Users should establish authority to store the data, provide required notices to their users, manage access, and arrange retention and deletion. See the [external service and privacy disclosure](../readme.txt) for what is sent and when.

AWS contracts and charges are between the user and AWS. Users bear storage, transfer, request and other applicable charges. Distribution of this product does not include AWS service fees.

## 4. Warranty and liability

Software warranty and liability are governed by the applicable GPL provisions. GPL version 2 addresses these in sections 11 and 12, including qualifications for applicable law and separate written agreements. See the full [LICENSE](../LICENSE).

The README's features and scope describe what the product preserves and restores. They do not establish a contract for managed operations, commissioned recovery work, recovery deadlines or compensation. This document adds no new disclaimer or restriction beyond the GPL.

## 5. Contact and document updates

Report problems through [GitHub Issues](https://github.com/ozekihiroshi/ozeki-wordpress-resilience/issues). Include the product version, operation and error, but omit private keys, credentials, personal data and private originals.

Document changes are available in repository history. Licenses accompanying distributed packages are retained.

Reference: [official GNU GPL version 2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html).
