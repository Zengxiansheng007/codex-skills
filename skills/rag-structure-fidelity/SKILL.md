---
name: rag-structure-fidelity
description: Preserve structural fidelity during document intake for local RAG. Use when admitting md/doc/docx/pdf/lakebook materials, comparing Yuque outlines with正文, deciding whether structure is recoverable, or blocking scanned/image-only PDFs and unrecoverable critical blocks.
---

# rag-structure-fidelity

把“结构可复原的文献”稳稳送入本地 RAG。第一版只做结构保真，不做治理裁决，不做下游包装。

## 适用场景

- 用户要把文档纳入本地知识库
- 用户要求只保留结构可复原的内容
- 用户提供 `md` 正文、`doc/docx/pdf` 或 `.lakebook`
- 用户要比较语雀目录与正文是否一致
- 用户要判断扫描件、图片型 PDF、表格、列表、图片引用是否可接受

## 核心规则

1. `md` 是唯一正文输入。
2. `.lakebook` / 语雀只用于目录对照和备用来源。
3. `doc/docx/pdf` 只在可结构化恢复时处理。
4. 扫描件和图片型 PDF 硬阻断。
5. 表格按整表判定，列表按整块判定。
6. 正文中的图片保留引用和位置，不内嵌二进制。
7. 关键规则区块必须能复原，否则阻断。
8. 只生成候选证据和候选映射，不自动生成 RC。
9. 不直接组下游包，统一交给 `rag-downstream-handoff`。

## 输出

- `admission_report`
- `reject_report`
- `structure_map.json`
- `evidence.json`
- `validation_report`

## 工作流程

1. 识别输入格式与来源类型。
2. 以 `md` 正文为主抽取结构。
3. 用 `.lakebook` 做目录对照，不进入正文抽取。
4. 按语义块判断可复原性。
5. 对关键区块、表格、列表、图片引用执行阻断或保留。
6. 生成候选证据与校验结果。
7. 需要人工确认时，停止在候选层。

## 永远不要

- 自动扫描未授权磁盘目录
- 读取账号、Cookie、Token、密钥或未脱敏生产数据
- 自动生成 RC
- 自动把候选映射当作正式真值
- 直接输出下游执行包

## 参考文件

- `references/structure-policy.md`
- `references/input-output-contract.md`
- `references/validation-checklist.md`

