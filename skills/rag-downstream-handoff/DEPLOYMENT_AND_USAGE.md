# rag-downstream-handoff Deployment And Usage

## Deploy
1. Copy this folder to `%USERPROFILE%\.codex\skills\rag-downstream-handoff`.
2. Preserve references and packet contract examples.
3. Confirm the target machine can read the intended RAG workspace, normally `D:\RAG`.
4. Restart Codex or open a new task.

## Use
Use `rag-downstream-handoff` to prepare read-only evidence packets for downstream agents such as `auto-testcase-generator`, `ui-test`, or Solution D.

```text
使用 rag-downstream-handoff 为 ui-test 生成只读证据包，不执行 UI 测试。
```

