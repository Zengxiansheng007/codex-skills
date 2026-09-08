# Publish Package Contract

`publish_package.py` is the fixed preflight and dry-run layer. It does not
silently push GitHub or call GitBook. A live adapter may be added only after the
target repository, branch, Space, permissions and sync direction are verified
and represented in an approved release manifest.

`release_adapter.py` is the approval-gated live adapter. It validates the exact
repository, branch, visibility and public path allowlist; stages only approved
paths; verifies the remote commit SHA; reads `GITBOOK_TOKEN` only from the
process environment; and verifies GitBook content, Space-to-Site linkage and
public Site state independently. GitHub success with an unverified GitBook
result is `partial`, never complete.

The package must pass manifest shape and digest validation, sensitive scanning,
approval matching and target repository matching. The result keeps GitHub and
GitBook outcomes separate. A dry-run with `preflight-passed` is not a publish
completion signal.

The live adapter must not mutate requirement anchors, create RC, persist
credentials or infer approval from a previous dry-run.

## Default Target Binding

Unless a caller supplies explicit overrides, `release_adapter.py` prepares the
release for these defaults:

- GitHub repository: `Zengxiansheng007/codex-skills`
- GitHub branch: `main`
- GitBook organization: `Nu93G7sN2JZ0YFbZODmd`
- GitBook Site: `site_xT2YU`
- GitBook Space: `q7JoIgovR7WYwPc7tCa0`
- public GitBook URL: `https://zengxiansheng.gitbook.io/skills/`

Defaults are routing convenience, not publication approval. The approval file
must still match `targetRepository`, `targetBranch`, `publishVisibility`,
`gitbookOrganizationId`, `gitbookSiteId`, `gitbookSpaceId`, and every approved
path root exactly. Explicit command-line overrides remain supported but fail
closed unless the approval file authorizes the same target.

Do not persist GitBook `~/changes/<number>/` URLs as release targets. They are
revision views; stable publication and verification use organization, Site and
Space IDs.
