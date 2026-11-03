在当前已通过 47 项测试与 8 项验收的短信 CSV 应用上做最后的小修复，不扩展功能。
1. app.py 的 async /predict-batch 在完整校验后，用 starlette.concurrency.run_in_threadpool 将整个逐条真实 Predictor 推理循环放在线程池，保序返回，继续复用原缓存。
2. static/app.js 的 buildStats 清洗总数应读取实际 dataset.cleaned_rows（5159），当前别名漏了该字段显示为横杠。
3. README 不引用继承的旧测试哈希作为本轮证明。说明模型资产复用、当前实际测试结果及未验证事项；哈希范围以真实记录为准。
保留原接口、样式、CSV 下载与真实资产。只输出必要修改文件，禁止修改资产。test 补充并实际运行回归，writer 更新简短 README，review 最后检查。仅安排 dev→test→writer→review。
