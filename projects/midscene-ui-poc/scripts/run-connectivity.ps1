$ErrorActionPreference = "Stop"
$bundledNode = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin"
if (Test-Path $bundledNode) {
  $env:PATH = "$bundledNode;$env:PATH"
}
& ".\node_modules\.bin\midscene.CMD" ".\cases\00-connectivity.yaml" "--headed" "--keep-window" "--summary" ".\reports\connectivity-summary.json"

