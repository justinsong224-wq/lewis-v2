# 短信分类演示案例

Lewis 复用已训练 Transformer，生成 FastAPI + 原生网页，提供单条英文短信分类、真实概率、实验对比和 CSV 批量预测增量。

模型不是本次由 Lewis 训练的；来源、哈希在 `backend/workspace/assets/sms/provenance.json`。原短信项目保持原样。

| 文件 | 用途 |
|---|---|
| requirement.md | 基础版完整需求 |
| batch-requirement.md | 现场增量需求 |
| presentation-fix.md | 基础版展示修复需求 |
| case.json | 通过验收的基础与增量任务编号 |
| messages.csv | 30 条中文短信：奇数条为正常消息，偶数条为明显诈骗示例，各 15 条；中文模型仍有误判 |
| test_acceptance.py | 5 项基础验收 |
| test_batch.py | 3 项批量验收，增量合计 8 项 |
| verification.md | 实际验证记录及证据位置 |

正式展示只开一个终端：

```powershell
backend/venv-sms/Scripts/python.exe -B start_demo.py
```

在 Cursor 打开 docs/答辩演示流程.md，按总文档操作。办公室“演示协作全流程”播放 32 秒预设动画，不调用模型或创建任务；已有生成应用用于真实预测和 CSV 操作。

需要真实增量开发时，在基础任务点击“基于当前任务增加 CSV 批量预测”，再提交开发需求。动画和真实任务独立，真实任务运行时演示按钮禁用。

