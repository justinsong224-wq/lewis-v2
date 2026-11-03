"""演示入口的页面布局；保留生成任务的原始文件。"""
from pathlib import Path
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


def install(app, workspace):
    assets = Path(__file__).resolve().parents[1] / 'demo/sms-classifier/presentation'
    app.mount('/presentation', StaticFiles(directory=str(assets)), name='presentation')
    report = assets.parent / 'chinese/research.html'
    if report.is_file():
        @app.get('/model-research', response_class=HTMLResponse)
        def model_research():
            return report.read_text(encoding='utf-8')
    from chinese_sms import DIRECTORY
    if (DIRECTORY / 'metrics.json').is_file():
        @app.get('/chinese-metrics')
        def chinese_metrics():
            import json
            return {key: json.loads((DIRECTORY / name).read_text(encoding='utf-8'))
                    for key, name in [('metrics', 'metrics.json'), ('dataset', 'dataset_stats.json')]}
    original = workspace / 'static/index.html'
    app.router.routes[:] = [route for route in app.router.routes if getattr(route, 'path', None) != '/']

    @app.get('/', response_class=HTMLResponse)
    def index():
        html = original.read_text(encoding='utf-8')
        html = html.replace('</head>', '<link rel="stylesheet" href="/presentation/layout.css?v=20261102b"></head>')
        html = html.replace('<main class="wrap">', '''<main class="wrap">
<nav class="view-tabs" role="tablist" aria-label="应用内容">
<button id="predict-tab" role="tab" aria-selected="true" aria-controls="prediction-view" tabindex="0">短信预测</button>
<button id="metrics-tab" role="tab" aria-selected="false" aria-controls="metrics-view" tabindex="-1">模型实验</button>
</nav>
<div id="prediction-view" role="tabpanel" aria-labelledby="predict-tab">''')
        marker = '<section class="card">' + chr(10) + '    <h2>实验结果</h2>'
        html = html.replace(marker, '''</div><div id="metrics-view" role="tabpanel" aria-labelledby="metrics-tab" hidden>
<section class="card">
    <h2>历史实验结果</h2>''')
        html = html.replace('</main>', '</div></main>')
        html = html.replace('<h2>历史实验结果</h2>', '<h2>英文历史实验结果</h2>')
        if (DIRECTORY / 'metrics.json').is_file():
            html = html.replace('<h3>模型流程</h3>', '''<h3>中文本轮实验</h3>
<p class="hint">中文字符级 Transformer 与字符 TF-IDF + 逻辑回归，使用相同数据划分。与上方英文历史实验分开统计。</p>
<div id="chinese-experiment"></div>
<p><a href="/model-research" target="_blank" rel="noopener">查看 Search Agent 模型对比补充调研</a>（本轮新增，非原始生成记录）</p>
<h3>模型流程</h3>''')
            html = html.replace('仅英文、概率未经校准、可能误判。', '英文使用原模型，含中文使用本轮中文 Transformer。中文训练语料规模较小，可能误判，概率未经校准；spam 表示垃圾短信，不是违法性认定。')
        return HTMLResponse(html.replace('</body>', '<script src="/presentation/layout.js?v=20261102b"></script></body>'), headers={'Cache-Control': 'no-store'})
