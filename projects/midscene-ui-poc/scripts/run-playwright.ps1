$ErrorActionPreference = "Stop"
$bundledNode = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin"
if (Test-Path $bundledNode) {
  $env:PATH = "$bundledNode;$env:PATH"
}
& ".\node_modules\.bin\playwright.CMD" "test" @args
