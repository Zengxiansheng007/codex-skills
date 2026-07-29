$ErrorActionPreference = "Stop"
$bundledNode = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin"
if (Test-Path $bundledNode) {
  $env:PATH = "$bundledNode;$env:PATH"
}
& ".\node_modules\.bin\midscene.CMD" "--config" ".\midscene.config.yaml" "--summary" ".\reports\yaml-summary.json"

