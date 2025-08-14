# Storage Task: S3/MinIO upload & retrieval

## Requirements

- Streamed uploads; MIME/type validation; size limits.
- Server-generated, time-limited signed URLs.
- Keys: user/tenant-safe, normalized.

## Steps

1) Server: signer util; PUT/GET presigners with content-type & size constraints.
2) API: route to obtain signed URL; DB record for object metadata.
3) Frontend: upload with fetch (stream if possible); handle 4xx/5xx; show progress.
4) Tests: signer units; API integration; a small end-to-end happy path.

## Output

- Diff + example usage.
