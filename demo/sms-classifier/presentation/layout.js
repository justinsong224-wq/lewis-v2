'use strict';
(() => {
  const chineseExperiment = document.getElementById('chinese-experiment');
  if (chineseExperiment) fetch('/chinese-metrics').then(r => {
    if (!r.ok) throw Error('实验数据读取失败');
    return r.json();
  }).then(({ metrics, dataset }) => {
    const table = document.createElement('table'); table.className = 'data';
    const head = table.createTHead().insertRow();
    ['模型', '准确率', '精确率', '召回率', 'F1'].forEach(text => {
      const th = document.createElement('th'); th.textContent = text; head.append(th);
    });
    const body = table.createTBody();
    ['baseline', 'transformer'].forEach(name => {
      const row = body.insertRow();
      [name === 'baseline' ? 'TF-IDF + 逻辑回归' : '中文 Transformer', ...['accuracy','precision','recall','f1'].map(k => (metrics[name][k]*100).toFixed(2)+'%')].forEach(value => { row.insertCell().textContent = value; });
    });
    const wrap = document.createElement('div'); wrap.className = 'table-scroll'; wrap.append(table);
    const note = document.createElement('p'); note.className = 'hint';
    note.textContent = '训练 '+dataset.train+' 条 / 验证 '+dataset.validation+' 条 / 测试 '+dataset.test+' 条。展示 CSV 未加入训练集。真实结果不保证 Transformer 优于 baseline。';
    chineseExperiment.append(wrap, note);
  }).catch(error => { chineseExperiment.textContent = error.message; });
  const batchBody = document.getElementById('batch-tbody');
  if (batchBody) {
    document.querySelectorAll('#batch-table th').forEach((cell, index) => {
      cell.textContent = ['短信内容', '预测分类', '不良概率', '正常概率'][index];
    });
    const observer = new MutationObserver(() => {
    observer.disconnect();
    batchBody.querySelectorAll('tr').forEach(row => {
      const cells = row.cells;
      if (cells[1]?.textContent === 'ham') cells[1].textContent = '正常';
      if (cells[1]?.textContent === 'spam') cells[1].textContent = '不良';
      if (cells[1]) cells[1].className = cells[1].textContent === '正常' ? 'label-normal' : 'label-risk';
      for (const cell of [...cells].slice(2)) {
        const value = Number(cell.textContent);
        if (cell.textContent && Number.isFinite(value) && !cell.textContent.includes('%')) cell.textContent = (value*100).toFixed(2)+'%';
      }
    });
    observer.observe(batchBody, { childList: true, subtree: true });
  });
    observer.observe(batchBody, { childList: true, subtree: true });
  }
  const result = document.getElementById('result');
  const resultObserver = new MutationObserver(() => {
    resultObserver.disconnect();
    const verdict = result.querySelector('.verdict');
    if (verdict) verdict.textContent = verdict.textContent.includes('spam') ? '预测结果：不良' : '预测结果：正常';
    result.querySelectorAll('.bar-label').forEach((cell, index) => { cell.textContent = index ? '正常概率' : '不良概率'; });
    result.querySelectorAll('.bar-num').forEach(cell => {
      if (!cell.textContent.includes('%')) cell.textContent = (Number(cell.textContent)*100).toFixed(2)+'%';
    });
    resultObserver.observe(result, { childList: true, subtree: true });
  });
  resultObserver.observe(result, { childList: true, subtree: true });
  document.getElementById('btn-spam').textContent = '不良短信示例';
  // 在演示入口替换按钮，保留历史任务中的原始示例与生成证据。
  const examples = {
    'btn-ham': 'Hi Alex, are we still meeting at the university library at six this evening? Please bring your laptop and the latest project notes so we can review the presentation together before dinner.',
    'btn-spam': 'Congratulations! You have been selected to receive a FREE cash prize of 1000 pounds. Call our claim line now and provide your payment details to release your reward. This exclusive offer expires tonight, so act immediately!',
  };
  document.addEventListener('DOMContentLoaded', () => Object.entries(examples).forEach(([id, text]) => {
    const original = document.getElementById(id);
    const button = original.cloneNode(true);
    original.replaceWith(button);
    button.addEventListener('click', () => { document.getElementById('sms-text').value = text; });
  }));
  const tabs = [...document.querySelectorAll('.view-tabs [role=tab]')];
  function select(tab) {
    tabs.forEach(item => {
      const active = item === tab;
      item.setAttribute('aria-selected', String(active));
      item.tabIndex = active ? 0 : -1;
      document.getElementById(item.getAttribute('aria-controls')).hidden = !active;
    });
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => select(tab));
    tab.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      const next = tabs[event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length];
      select(next);
      next.focus();
    });
  });
})();
