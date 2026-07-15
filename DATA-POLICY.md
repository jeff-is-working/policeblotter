# Data ethics, sourcing, and takedown policy

This project republishes public records. With that comes responsibility. These
rules are binding on the code and on anyone operating this pipeline.

## Sourcing

- Only data that agencies publish publicly is ingested. No authenticated access,
  no circumvention of access controls.
- Requests identify themselves with a descriptive User-Agent and are rate-limited.
  We poll no more often than needed to capture daily churn.
- Raw source snapshots are archived under `data/raw/` for provenance and auditing.

## Hard constraints (enforced in code, see `ingest/schema.py`)

- **No mugshots / photos.** `strip_media` drops any image-like field at ingestion.
- **No person-name field** in normalized data. `strip_names` removes name-like
  fields; the `Record` type has no name attribute.
- **No name search or indexing.** The site is `noindex` with a disallow-all
  `robots.txt`; the client exposes only date and location filters.

## Presumption of innocence

Booking and arrest records reflect **allegations**, not convictions. Every page
that shows booking data states that people are presumed innocent unless convicted.

## Retention and correction

- Records are retained to provide a historical transparency archive. If a source
  publishes a correction, re-ingestion reflects it on the next run.
- **Takedown / correction requests:** open a GitHub issue using the takedown
  template, or contact the maintainer. Legitimate requests (sealed/expunged records,
  data that is not actually public, factual errors) are honored promptly.

## Not legal advice

This repository does not provide legal advice. Operators are responsible for
compliance with Washington public-records law and applicable regulations.
