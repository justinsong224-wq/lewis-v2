"""从已保存的调研结果导出报告，不修改历史任务或调用模型。"""
from html import escape


def report_markdown(task):
    snapshot = task.get('snapshot') or {}
    research = (snapshot.get('agent_results') or {}).get('search')
    if not research:
        return None
    def describe(value):
        if isinstance(value, dict):
            return ' · '.join(str(v) for v in value.values())
        return str(value)
    lines = ['# 技术调研报告', '', f"任务编号：{task['id']}",
             '', '## 开发需求', '', task.get('user_input') or '未记录',
             '', '## 搜索关键词', '', describe(research.get('query') or '未记录'),
             '', '## 调研结论', '', describe(research.get('error') or research.get('summary') or '未记录')]
    for title, key in [('实现建议', 'key_points'), ('参考来源', 'sources')]:
        lines.extend(['', '## ' + title, ''])
        values = research.get(key) or []
        if not isinstance(values, list):
            values = [values]
        lines.extend(['- ' + describe(v) for v in values] or ['未记录'])
    decisions = (snapshot.get('plan') or {}).get('research_decisions') or []
    lines.extend(['', '## 技术方案采纳情况', ''])
    for decision in decisions:
        lines.append('- ' + ('采纳' if decision.get('adopted') else '未采纳') + '：'
                     + str(decision.get('source', '')) + ' — ' + str(decision.get('reason', '')))
    if not decisions:
        lines.append('尚未记录采纳情况。')
    lines.extend(['', '说明：本报告由任务中保存的调研内容整理导出，不代表重新搜索或重新验证来源。', ''])
    return chr(10).join(lines)


def report_html(markdown):
    import re
    sections = {}
    current = '记录信息'
    for line in markdown.splitlines():
        if line.startswith('## '): current = line[3:]
        elif line.strip() and not line.startswith('# '): sections.setdefault(current, []).append(line)
    def highlight(text):
        safe = escape(text)
        return re.sub(r'(baseline|Transformer|TF-IDF|LogisticRegression|F1|未查证|未检索到|不能宣称|数据泄漏|同一训练/验证/测试划分|\d+(?:\.\d+)?%)', r'<strong>\1</strong>', safe, flags=re.I)
    blocks = ['<header><span>LEWIS · SEARCH AGENT</span><h1>技术调研报告</h1><p>先看结论，再看建议，来源与原始需求按需展开。</p></header>']
    conclusion = sections.pop('调研结论', [])
    blocks.append('<section class="conclusion"><span class="badge">核心结论</span>' + ''.join('<p>'+highlight(v)+'</p>' for v in conclusion) + '</section>')
    if 'sms-model-comparison-supplement' in markdown:
        from pathlib import Path
        import json
        path = Path(__file__).resolve().parent / 'workspace/assets/sms/chinese/metrics.json'
        if path.is_file():
            metrics = json.loads(path.read_text(encoding='utf-8'))
            rows = ''.join('<tr><th>'+name+'</th>'+''.join('<td>'+format(metrics[key][k]*100,'.2f')+'%</td>' for k in ['accuracy','precision','recall','f1'])+'</tr>' for key,name in [('baseline','TF-IDF + 逻辑回归'),('transformer','中文 Transformer')])
            blocks.append('<section><h2>本地实测对比</h2><div class="table-wrap"><table><thead><tr><th>模型</th><th>准确率</th><th>精确率</th><th>召回率</th><th>F1</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="notice">同一数据划分的本地实验。baseline 本轮略高，不能据此认定任何模型普遍更优。外部来源与本地指标分开判断。</p></section>')
    suggestions = sections.pop('实现建议', [])
    blocks.append('<section><h2>关键建议</h2><div class="cards">'+''.join('<article><span class="number">'+str(i+1).zfill(2)+'</span><p>'+highlight(v.removeprefix('- '))+'</p></article>' for i,v in enumerate(suggestions))+'</div></section>')
    for title, values in sections.items():
        content = []
        for value in values:
            url = value.removeprefix('- ').strip()
            if title == '参考来源' and re.match(r'^https?://[^\s]+$', url):
                content.append('<p><a href="'+escape(url,quote=True)+'" target="_blank" rel="noopener noreferrer">'+escape(url)+'</a></p>')
            else: content.append('<p>'+highlight(value)+'</p>')
        blocks.append('<details'+(' open' if title == '参考来源' else '')+'><summary>'+escape(title)+'</summary>'+''.join(content)+'</details>')
    return ('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>技术调研报告</title><style>'
            'body{max-width:1060px;margin:32px auto;padding:0 20px 48px;background:#f2f5fc;color:#24324c;font:15px/1.85 system-ui,sans-serif;overflow-wrap:anywhere}'
            'header{background:linear-gradient(120deg,#154cb2,#6638be);color:white;padding:30px;border-radius:18px}header span{font-size:12px;letter-spacing:2px}h1{margin:8px 0;font-size:30px}header p{margin:0;color:#e1eaff}'
            'section,details{background:white;padding:24px;margin-top:20px;border-radius:14px;border:1px solid #e0e6f1}h2{font-size:20px;margin:0 0 16px}.conclusion{border-left:6px solid #6450df;background:#f2efff}.conclusion p{font-size:17px;margin-bottom:0}.badge{display:inline-block;background:#6346cc;color:white;border-radius:6px;padding:3px 12px;font-weight:700}'
            'strong{color:#a13f13;background:#fff0cf;border-radius:3px;padding:0 3px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,360px),1fr));gap:14px}article{background:#f7f9ff;border:1px solid #e1e7f5;border-radius:10px;padding:16px}.number{font-size:21px;color:#365fd4;font-weight:800}article p{margin:6px 0}.notice{background:#fff6dc;border-left:4px solid #edac21;padding:12px}summary{font-weight:700;cursor:pointer;color:#214bb0}a{color:#225bd0}p{white-space:pre-wrap}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;white-space:nowrap}td,th{text-align:left;padding:12px;border-bottom:1px solid #dce4f0}thead{background:#eaf0ff}td:last-child{color:#195fa4;font-weight:800}@media(max-width:600px){body{padding:0 12px}header,section,details{padding:18px}h1{font-size:25px}}'
            '</style>'+''.join(blocks)+'</html>')
