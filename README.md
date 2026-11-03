# Lewis 软件开发协作系统

在现有 FastAPI、LangGraph、MCP、SQLite 和 Vue 工作台上，组织角色完成需求分析、调研、规划、开发、测试、文档和审查，保存实际产物与执行证据。

正式演示为英文短信分类：复用已有 Transformer 模型，Lewis 开发可运行页面、API、真实测试和 CSV 批量预测增量。模型不在本次重新训练。

## 启动

从仓库根目录，只开一个终端执行：

```powershell
backend/venv-sms/Scripts/python.exe -B start_demo.py
```

出现“全部启动完成”后，在 Cursor 打开 docs/答辩演示流程.md，按总文档操作。终端保持运行，演示结束按 Ctrl+C 统一停止；有真实任务时先等任务结束。
办公室顶部点击“演示协作全流程”，32 秒展示预设角色状态与流动线路，不调用模型、不创建任务。真实开发仍用“提交开发需求”。

短信演示使用 D 盘 backend/venv-sms；原环境保留。配置使用根目录 .env，字段见 [.env.example](.env.example) 和 [模型配置](docs/model-config.md)。支持 OpenAI 兼容 Chat Completions，换模型后需验证格式与效果。

生成文件在 backend/workspace/tasks，案例库在 backend/workspace/validation/sms-history.db，模型资产在 backend/workspace/assets/sms。这些是本地运行数据，复制源码时需要另行保留。

## 文档与检查

- [答辩演示全流程](docs/答辩演示流程.md)

- [项目说明](docs/重构后项目说明.md)

- [短信案例验收](demo/sms-classifier/verification.md)
- [Edge 浏览器环境](browser-lab/README.md)

后端：`backend/venv-sms/Scripts/python.exe -B -m unittest discover -s backend/tests -v`。前端目录：`npm test`、`npm run build`。

系统使用单进程。生成任务有独立目录和角色权限；部署执行环境仍应由使用者管理。



