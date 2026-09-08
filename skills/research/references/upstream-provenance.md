# Upstream provenance

Official source: https://github.com/anysearch-ai/anysearch-skill

Reference v3.1.1 resolved to commit 15b7ea5039983c9dee328be8c7c609f3eb86058e. The sibling payload preserves original files byte-for-byte except the GitHub-only .github directory is not packaged. LICENSE and NOTICE are retained.

The router consumes the official Skill capability/HTTP contract but does not execute the anonymous-enabled upstream CLI. Its guard uses standard-library HTTP and validates the pinned payload before sending requests. See upstream-manifest.json for every included path/hash.

An unknown error is not evidence of quota exhaustion. Exact known quota symbols use a conservative compatibility map; live error semantics remain an environment-validation item. Do not silently update the manifest after a hash mismatch.
