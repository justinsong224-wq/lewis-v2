修复当前短信分类基础版的展示问题，保留 /predict、/metrics、真实 Predictor、实验资产、所有功能。不要增加 CSV（本轮仍为基础版）。只修改确有必要的前端文件。
实际浏览器证据：390px 窄屏 document.scrollWidth > innerWidth。实验区完整展开了 dataset.config、64 字符哈希和全部原始指标，既难读又撑开布局。
将实验区改成紧凑中文表格，只展示 baseline 与 transformer 的准确率和 F1（百分比两位小数，数据仍来自 /metrics），旁边显示清洗总数、训练/验证/测试条数。其余数据放折叠“原始实验数据”，长哈希/JSON 用 overflow-wrap:anywhere，表格包局部滚动容器，不允许整页横向溢出。保留来源说明、模型流程与英文限制。
同步修改 test_app.py 验证基本页面和原接口不变；注意 trim 后 5000 字合法，5001 才报 422。使用真实模型测试，不修改资产。writer 更新 README，review 检查窄屏样式，但未运行浏览器不得声称实测通过。只规划 dev→test→writer→review。
