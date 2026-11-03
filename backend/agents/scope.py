"""最小业务案例的角色边界；普通开发任务仍按自身需求执行。"""
def scope_note(context, role):
    profile = (context or {}).get('acceptance_profile')
    if profile in ('sms-classifier', 'sms-batch'):
        return {
            'dev': '短信案例：复用 SMS_ASSET_DIR 的真实 Predictor 与实验资产，只写页面/API，不重训、不伪造、不修改资产。严格文件块，无前言或后记。',
            'test': '只输出 test_app.py 严格文件块，禁止任何额外文字。真实模型测试，继承 SMS_ASSET_DIR，避免 mock 推理；不要求任意短信必然分类正确。',
            'writer': '简短 README，明确原模型资产复用和 Lewis 开发范围、启动所需 SMS_ASSET_DIR、真实测试与未验证项。',
            'review': '核对实际实现、真实模型加载、输入校验、页面和来源说明，避免无关架构要求。',
            'customer': '简短说明实际产物与结果，分清复用模型和本轮代码，不虚构训练或浏览器验证。',
        }.get(role, '')
    return ''
