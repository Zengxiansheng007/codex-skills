# Source Ranking Policy

Use source type by claim type. Do not use a single global domain ranking.

| Claim type | Preferred sources | Supporting sources | Avoid as primary |
|---|---|---|---|
| Normative rule | Formal standard, RFC, regulator, official policy | Expert commentary | Blog summaries |
| API usage | Versioned official docs, schema, real response, SDK source | Issues, examples | Outdated tutorials |
| Implementation behavior | Local runtime observation, version-pinned source, tests | Maintainer comments | Floating `main` links |
| Release/change | Release note, changelog, commit, PR, package registry | Issue discussion | SEO articles |
| Security | CVE/NVD/CISA/vendor advisory, OWASP, NIST | Security blogs with PoC | Unverified social posts |
| Academic result | Primary paper, systematic review, dataset card | Lab blog, conference talk | Citation-count-only claims |
| Product comparison | Official pricing/docs plus independent benchmark | User reviews | Vendor-only marketing |
| Community practice | High-signal issue/forum/Q&A | Blog examples | Aggregator pages |

For each source record:

```text
id, title, url, publisher, author, publishedAt, accessedAt,
version, claimTypes, authority, directness, independence,
reproducibility, limitations, contentHashOrStableId
```

Evidence quality depends on fit to claim type, directness, version applicability, independence, reproducibility, and conflict status.
