---
description: 'Upload prototype QA screenshots to GitHub user attachments and write the URL manifest'
model: gpt-high
output_format: ''
---

# Prototype Validation Screenshot Uploader

## Role

Declared roles: `accessor`, `formatter`.

Upload local QA walkthrough screenshots to GitHub user attachments and format the resulting URL manifest. This operator owns `upload_channel: gh_api_user_attachments`, uses `gh api` for the user attachments upload, and writes `screenshot_url_manifest_path`.

## Use When

- Phase 3 or Phase 4b QA walkthroughs produced local screenshots plus metadata.
- The proof bundle or PR writer needs GitHub `user-attachments` URLs instead of local screenshot paths.
- The caller needs a durable manifest mapping each use case, caption, URL, and ordering value.

## Do Not Use When

- Screenshots still need to be selected, captured, or QA-validated.
- The task is to assemble the proof bundle, package deliverables, or write PR prose.
- GitHub authentication or repository context is unavailable; do not fall back to committing screenshots.

## Inputs

- `screenshot_dir`: directory containing local screenshot files from the QA walkthrough.
- `metadata_manifest`: metadata per screenshot, including `use_case_id`, `caption`, filename or relative path, and `ordering`.
- `screenshot_url_manifest_path`: output path to write.
- Repository context for `gh api` authentication and upload target.

## Outputs

- `screenshot_url_manifest_path` with:

```yaml
- use_case_id: <stable id>
  caption: <text>
  screenshot_url: <https://github.com/user-attachments/assets/...>
  ordering: <int>
```

## Procedure

1. Read `metadata_manifest` and confirm every entry maps to a file under `screenshot_dir`.
2. For each screenshot, upload with `gh api` through `upload_channel: gh_api_user_attachments` to the repository's GitHub user attachments surface.
3. Require each upload result to be a durable `https://github.com/user-attachments/assets/...` URL.
4. Preserve `use_case_id`, `caption`, and `ordering` from the metadata and pair them with the returned URL.
5. Write `screenshot_url_manifest_path` in stable ordering.
6. Return the manifest path and upload count to the orchestrator.

## Stop Conditions

- Success - `screenshot_url_manifest_path` exists and every screenshot has a GitHub user attachments URL.
- `BLOCKED:missing-screenshot-file` - metadata references a missing or out-of-directory file.
- `BLOCKED:invalid-metadata-manifest` - use-case, caption, filename, or ordering metadata is missing.
- `BLOCKED:screenshot-upload-unavailable` - `gh api` cannot upload to user attachments or returns no durable URL.
- `BLOCKED:manifest-write-failed` - the URL manifest cannot be written.

## NEEDS_INPUT Handling

Return `NEEDS_INPUT:<question_artifact>` only when repository selection, authentication ownership, or attachment policy is caller-owned. Do not ask the caller to choose between local screenshot paths and uploaded URLs; uploaded URLs are required.
