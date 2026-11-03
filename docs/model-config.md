# 接入模型平台

Lewis 使用 OpenAI 兼容的 Chat Completions 协议，不要求阿里云账户。
支持提供该协议的平台与第三方网关；仅提供原生 Messages、Responses 或自定义协议的服务需要另加适配，不能只换 URL。

编辑仓库根目录 .env，填写以下配置（占位值需要替换，不要提交真实 Key）：

```dotenv
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://your-provider.example/v1
LLM_MODEL=your-provider-model-id
LLM_JSON_MODE=auto
```

LLM_BASE_URL 使用服务商给出的基础地址，保留其 /v1、/api/v3 等真实路径。
若粘贴以 /chat/completions 结尾的完整地址，系统会去掉该后缀，避免重复拼接。
模型名称必须使用新平台支持的 ID，切换平台时不要沿用默认模型名称。
配置固定从根目录 .env 读取，与启动目录无关；系统环境变量优先于 .env。
修改后重启后端，已执行的历史任务和文件不受影响。

## 配置规则

模型配置统一使用 LLM_API_KEY、LLM_BASE_URL、LLM_MODEL，不提供服务商专属别名。
代码不内置任何平台地址或模型名称，三项必须显式填写；不会根据 Key 猜测服务商。
搜索仍独立使用 SERPER_API_KEY，不随模型 Key 切换。

## JSON 输出兼容

- auto：先请求 JSON Object 模式；仅当接口明确返回不支持 response_format/json_object 的 400 参数错误时，移除该参数再请求一次，并继续严格解析 JSON。
- json_object：要求服务支持 JSON Object 参数，不做兼容回退。
- prompt：不发送 response_format，通过提示词要求 JSON，适合已知不支持该参数的平台。

兼容回退可能多消耗一次请求。401、403、限流、超时及其他参数错误不会触发 JSON 参数回退。
SDK 禁用网络/临时服务错误自动重试，避免超时后重复发送长生成请求。
LLM_TIMEOUT_SECONDS（默认 90）是单次模型请求的总时限，覆盖客户端建立、请求响应及明确不支持 JSON 参数时的降级尝试；AGENT_TIMEOUT_SECONDS（默认 240）限制整个角色，包括工具和可能的一次 JSON 纠正。两者必须大于 0。若模型长生成需要更多时间，应按实测配置，并为多次模型请求及工具执行留出角色总时限，不盲目增加等待。
模型适配器以 INFO 日志记录完成请求的耗时、输入字符数及平台报告的输入/输出 token 数；启用 agents.base 的 INFO 日志可见。不记录请求正文、Key 或原始响应。失败与总时限在 WARNING 日志记录错误类型和耗时；这些信息不能单独证明额度耗尽。
输出为数组、空文本、截断或非法 JSON 时明确失败，不将其当成有效角色结果。
对 JSON 字符串内未转义的控制字符作有限兼容；其他 JSON 语法错误最多请求模型纠正一次，仍无效就失败。
格式纠正会增加请求与 token 消耗，受角色总超时限制，不保证能纠正成功。

## 检查连接

仓库根目录执行（发送一次最小模型请求，auto 模式可能兼容重试）：

```powershell
backend/venv/Scripts/python.exe -B backend/check_model.py
```

检查只显示地址、模型、JSON 模式和错误类型，不输出 Key 或服务商原始错误正文。
connection=ok 且 json_ok=true 后，再运行完整演示任务。
接口连通不代表生成质量达标，换模型后仍需通过固定业务验收。
