在已有短信分类应用中只增加 CSV 批量预测与结果下载，保留单条预测、真实模型、实验展示和样式，不改资产不训练。
POST /predict-batch 接收 Content-Type: text/csv 的 UTF-8 原始 CSV 文本（不是 multipart），必须有 text 列，1—100 行，逐行 text trim 后 1—5000 字；缺列/空表/空行/超限/无效 UTF-8 返回 422。先验证全部输入再逐条调用原缓存 Predictor。返回 {results:[{text,label,spam_probability,ham_probability},...]}，保持顺序。请求体最多 1MB，超限 413。
页面新增“CSV 批量预测”区域，文件选择（label“选择 CSV 文件”），按钮“批量预测”，结果表和“下载结果 CSV”。通过 file.text() 读取并提交原文本；失败显示错误，清除旧表与下载，禁止下载旧结果。下载标准 CSV（UTF-8 BOM），字段 text,label,spam_probability,ham_probability，正确处理逗号双引号换行，并防电子表格公式注入（text 以 = + - @ 开头时前置单引号）。默认最多 100 行，不添加其他功能。先读取已有文件，只输出修改文件，补测试和 README。
