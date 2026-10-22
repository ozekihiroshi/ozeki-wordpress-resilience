# Signed reconstruction kit ZIP candidate

Experimental 0.1.0-dev.1; no publication or production changes. English README is primary; RAADME-jp.md describes the same scope.

Build using tools/build-release.py into a new candidate directory. Verify manifest SHA256 and every extracted file. Install the plugin ZIP using actual WordPress Plugin_Upgrader in an isolated generated-data environment; test fresh activation and overwrite of the previously verified portable-final-v2 candidate. Preserve plugin options, cron, wp-config, requests and external reports/history through deactivate/reactivate.

Extract the development kit into a new directory. Run its own signature, fixed-version, planner, comparison and distribution tests. Preserve separately stored synthetic root receipts, approvals, public trust pins, configuration, retrieval records and reconstruction history by before/after hashes. Keep the old code directory untouched. Run the packaged CLI's help and unsigned-fetch refusal without AWS calls. No private key, credential, downloaded runtime image or actual recovery dataset belongs in the ZIP.

This validates distribution integrity and lifecycle preservation, not another S3 transfer, OS reboot, full reconstruction or schema migration. Prior live S3/signature/reconstruction evidence remains a separate scope. Account independence and Docker compatibility limits remain. Final artifact hashes and acceptance results are recorded after freeze in evidence-public/rbr-signed-kit-zip.json; that generated report is not retroactively included in the tested archives.

Prerequisite: install Composer dependencies from the shipped composer.lock before PHP tests. Vendor libraries are deliberately not in the ZIP. The first packaging trial stopped at this missing prerequisite before WordPress installation; final-v2 makes it explicit and uses the existing local Composer cache without network. Packaged source files are checked independently of the generated vendor directory.
