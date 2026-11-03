# 中文训练补充

本轮由开发助手新增训练与语言路由，独立于 Lewis 历史生成任务；未修改原任务文件或英文资产。

数据：Lambozhuang/sms-spam-chinese 的 data/chinese-sms.csv，Git blob 208b216410ff5c7c8b5a29f12224054f5104ad2d。上游未声明明确许可证，原始数据仅本地评估，不分发。来源、文件哈希、划分哈希和权重哈希在 backend/workspace/assets/sms/chinese/provenance.json。

去重、排除冲突和30条演示文本后，每类随机抽10000条，seed=42；训练14000、验证3000、测试3000。TF-IDF与词表仅在训练集拟合，Transformer以验证集F1选轮次，测试集只评估最终模型。未进行近重复模板去重，因此测试指标不能代表跨来源泛化。

运行：backend/venv-sms/Scripts/python.exe -B backend/train_chinese_sms.py --data demo/sms-classifier/chinese/source.csv --epochs 15 --per-class 10000

baseline：字符1–3元TF-IDF + LogisticRegression；Transformer：中文字符 + 英文词，64维、1层、4头，最大192个token，超长文本截断。测试准确率分别97.60%和97.13%，F1分别97.60%和97.14%。当前中文推理使用Transformer，baseline仅作实验对照，不能宣称Transformer更好。

30条自写展示文本未加入训练/验证/测试，判对24条；demo-validation.json记录误判。中文结果是垃圾短信分类，不是法律认定，不能保证识别所有诈骗。

research.json、research.md、research.html：本轮真实调用Lewis Search Agent与Serper的补充调研，包含工具记录。原调研报告不覆盖。应用“模型实验”和Lewis任务详情均有入口。
