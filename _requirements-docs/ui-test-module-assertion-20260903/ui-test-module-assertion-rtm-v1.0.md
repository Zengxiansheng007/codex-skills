# UI-Test 逐模块断言修复 RTM v1.0

| Requirement | Design | Implementation | Test/Evidence | State |
|---|---|---|---|---|
| FR-01/02/04 | PageModuleRegistry + compile gate | v2 schemas, `compiler_v2.py` | compiler negative tests | passed-workspace |
| FR-03 | Test Data expected defaults | A/B `test-data.json` | adapter contract tests | passed-workspace |
| FR-05 | shared Resolved step model | compiler renderers | projection tests | passed-workspace |
| FR-06 | deterministic module readers | `formal_operations.py` | A 12-step and B 13-step formal qualifications | passed |
| FR-07 | recursive aggregate | `render_product_aggregate_v2` | Tianjin aggregate Golden | passed-workspace |
| FR-08 | structural formal verifier | `verify_formal_deployment.py` | valid/in_sync/ready; 336 historical files unchanged | passed |
| FR-09/10 | prepare/activate + qualification | `case_sync.py`, `formal_deploy.py`, `formal_runtime.py` | both zero-submit qualifications and activation result | passed |
| AC-07 | global/public release | install/publish workflow | 243 installed tests; GitHub main and Raw files verified | passed |
