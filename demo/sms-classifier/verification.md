# 短信案例验收记录

| 版本 | 任务编号 | 角色测试 | 固定验收 |
|---|---|---|---|
| 基础版 | 7142e073-6812-4036-bdd4-e2bd341491e8 | 20/20 | 5/5 |
| CSV 最终版 | a894fbc6-726c-469a-b693-7506ad5d72ac | 61/61 | 8/8 |

两项任务均已完成。最终版曾因额度耗尽在交付汇总失败，换配置后核对全部代码和测试哈希，仅重试汇总成功；原失败快照与事件保留。

2026-10-28 最终应用 Edge 2/2：真实单条预测、实验展示、390px 布局、CSV 批量、BOM、引号逗号换行转义、公式保护和错误清理全部通过。平台后端含恢复回放测试 58/58 回归通过；旧工单专用两项测试移除，通用约束测试保留迁移。

- 浏览器脚本：browser-lab/sms/sms.spec.js。
- 截图：browser-lab/artifacts/sms-a894fbc6-726c-469a-b693-7506ad5d72ac.png 和 sms-batch-a894fbc6-726c-469a-b693-7506ad5d72ac.png。
- 代码：backend/workspace/tasks/任务编号/。
- 测试：任务目录 .lewis/test-results.xml 和 .lewis/acceptance.json。
- 生成事件：backend/workspace/validation/sms-evidence/，含全部父任务。
- 数据库：backend/workspace/validation/sms-history.db。
- 原失败快照：validation/a894fbc6-726c-469a-b693-7506ad5d72ac.before-delivery-retry.json。

浏览器在角色结束后补验，原始交付和 README 可能保留当时“浏览器未验证”；后续实测以本记录为准，不改写历史。模型、推理和实验资产复用原短信项目，没有重新训练，来源见 assets/sms/provenance.json。

旧工单清理路径见 cleanup-manifest.json。

真实后端 Edge 联调 3/3 通过：文件预览下载、刷新、完整及续接 WebSocket 回放。前端状态测试和生产构建通过。恢复任务的旧终态会作为历史保留，回放以最新终态结束。
工作台 Edge 检查五项首次通过，历史刷新项首次超过 30 秒，单独复核 21.8 秒通过；没有隐去首次超时。新模型配置已成功完成交付汇总，尚未用新模型重跑完整开发。
一键入口 start_demo.py 已实际验证：单终端启动四个服务并通过 HTTP 就绪检查，Ctrl+C 后四个端口均释放；不调用模型。
新增纯前端32秒协作演示：Edge 使用模拟时钟验证阶段切换、线路激活、自动结束、停止和退出恢复；监测POST次数为0。前端构建通过。这是预设动画验证，不是新模型开发验证。
