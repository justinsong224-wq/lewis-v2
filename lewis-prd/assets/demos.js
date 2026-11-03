(function () {
  var $ = function (id) { return document.getElementById(id); };

  /* ---------- mermaid ---------- */
  if (window.mermaid) {
    mermaid.initialize({ startOnLoad: true, theme: 'neutral', securityLevel: 'loose' });
  }

  var AGENTS = ['CEO', 'PM', 'Search', 'Dev', 'Test', 'DevOps', 'Review', 'Analyst', 'Writer', 'Customer'];
  var STATUS_TEXT = {
    working: '执行中', done: '完成', error: '失败', skipped: '跳过', idle: '待命'
  };

  function buildFlow(labelsEl, barEl) {
    AGENTS.forEach(function (a) {
      var l = document.createElement('span'); l.textContent = a; labelsEl.appendChild(l);
      var s = document.createElement('div'); s.className = 'seg'; s.dataset.agent = a; barEl.appendChild(s);
    });
  }
  function setSeg(barEl, agent, status) {
    var seg = barEl.querySelector('.seg[data-agent="' + agent + '"]');
    if (!seg) return;
    seg.className = 'seg' + (status && status !== 'idle' ? ' s-' + status : '');
  }
  function resetBar(barEl) {
    barEl.querySelectorAll('.seg').forEach(function (s) { s.className = 'seg'; });
  }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  /* ---------- FR-1 任务提交 ---------- */
  (function () {
    var input = $('demo-task-input'), btn = $('demo-task-send'), result = $('demo-task-result');
    if (!input) return;
    function refresh() { btn.disabled = input.value.trim() === ''; }
    input.addEventListener('input', refresh);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !btn.disabled) btn.click();
    });
    btn.addEventListener('click', function () {
      btn.disabled = true; btn.textContent = '处理中…';
      result.innerHTML = '正在提交任务…';
      setTimeout(function () {
        result.innerHTML = '<span class="ok">任务已创建</span> · task_id: 7f3a-2c9e-41b8（演示）· 正在建立 WebSocket 连接接收事件…';
        btn.textContent = '发送'; refresh();
      }, 1200);
    });
    refresh();
  })();

  /* ---------- FR-3 任务流进度 ---------- */
  var WORK_MSG = {
    CEO: '正在分析并拆解任务…', PM: '正在编写 PRD 与开发任务…', Search: '正在检索参考资料…',
    Dev: '正在实现排序 API 并写入文件…', Test: '正在编写并执行测试用例…', DevOps: '正在准备部署与运行环境…',
    Review: '正在审查代码质量…', Analyst: '正在查询并分析数据…', Writer: '正在撰写交付文档…',
    Customer: '正在整合全部产出…'
  };
  (function () {
    var labels = $('demo-flow-labels'), bar = $('demo-flow-bar');
    var cur = $('demo-flow-cur'), st = $('demo-flow-st'), btn = $('demo-flow-run');
    if (!bar) return;
    buildFlow(labels, bar);
    btn.addEventListener('click', async function () {
      btn.disabled = true; resetBar(bar);
      for (var i = 0; i < AGENTS.length; i++) {
        var a = AGENTS[i];
        setSeg(bar, a, 'working');
        cur.textContent = a; st.textContent = 'working · ' + (WORK_MSG[a] || '执行中…'); st.style.color = 'var(--st-working)';
        await sleep(430);
        setSeg(bar, a, 'done');
        st.textContent = 'done · ' + a + ' 完成'; st.style.color = 'var(--st-done)';
        await sleep(110);
      }
      cur.textContent = '全部完成'; st.textContent = 'completed · 任务已交付'; st.style.color = 'var(--st-done)';
      btn.disabled = false;
    });
  })();

  /* ---------- FR-4 实时执行日志 ---------- */
  var LOG_QUEUE = [
    { t: '14:32:40', a: 'Dev', cls: 'agent', m: '开始执行：实现 Flask 排序 API…', d: '开始执行子任务 t2：实现 POST /sort 排序接口（支持升序 / 降序参数）。计划写入 workspace/app.py，并附带 pytest 测试文件，完成后提交 Git。' },
    { t: '14:32:44', a: 'Dev', cls: 'agent', m: 'filesystem/write_file → app.py 已写入', d: '调用 MCP 工具 filesystem/write_file，向 workspace/app.py 写入 Flask 应用（约 60 行）：POST /sort 接收数组与排序方向参数，返回排序结果与耗时。写入成功。' },
    { t: '14:32:45', a: 'Dev', cls: 'agent', m: 'git/git_commit → feat: 排序 API 初版', d: '调用 git/git_add 暂存 app.py、test_app.py，随后 git/git_commit 提交，提交信息：feat: 排序 API 初版（含测试）。' },
    { t: '14:32:46', a: 'Dev', cls: 'agent', m: '完成：2 个文件已提交', d: '子任务 t2 完成。产出：workspace/app.py（Flask 排序 API）、workspace/test_app.py（pytest 用例），均已提交 Git。' },
    { t: '14:32:46', a: 'Test', cls: 'agent', m: '开始执行：编写 pytest 测试用例…', d: '开始执行子任务 t3：为 /sort 接口编写测试，覆盖空数组、单元素、升序、降序与非法输入五类场景。' },
    { t: '14:33:02', a: 'Test', cls: 'agent', m: '完成：8 个用例全部通过', d: '测试执行完成：8 个用例，全部通过（pass_rate 100%）。测试报告已生成，覆盖正常排序、边界值与异常输入。' },
    { t: '14:33:02', a: 'Writer', cls: 'agent', m: '开始执行：撰写使用说明文档…', d: '开始执行子任务 t4：基于 Dev 与 Test 的产出，撰写 API 使用说明（调用方式、参数说明、示例请求与响应）。' },
    { t: '14:33:20', a: 'Customer', cls: 'customer', m: '任务完成 · 已生成最终交付说明', d: '全部子任务执行完毕。交付物：app.py（排序 API 实现）、test_app.py（8 个用例全部通过）、API 使用说明文档；Git 提交 2 次。任务状态置为 completed。' }
  ];
  var LOG_INIT = [
    { t: '14:32:05', a: 'CEO', cls: 'ceo', m: '正在分析并拆解任务…', d: 'CEO Agent 开始分析用户任务："实现一个带 pytest 测试的 Flask 排序 API，并给出使用说明"。' },
    { t: '14:32:11', a: 'CEO', cls: 'ceo', m: '任务拆解完成，共 4 个子任务', d: '拆解结果：t1 pm（需求说明）→ t2 dev（实现排序 API）→ t3 test（编写并执行测试）→ t4 writer（使用说明文档）。执行顺序：t1 → t2 → t3 → t4。' },
    { t: '14:32:11', a: 'PM', cls: 'agent', m: '开始执行：编写排序 API 的需求说明…', d: 'PM Agent 开始执行子任务 t1：梳理排序 API 的功能需求、接口契约与验收标准，输出可执行的开发任务清单。' },
    { t: '14:32:26', a: 'PM', cls: 'agent', m: '完成：PRD 与开发任务已生成', d: '子任务 t1 完成。产出 PRD 摘要：POST /sort 接口，参数 array（数字数组）与 order（asc/desc，默认 asc），返回排序后数组与处理耗时。' },
    { t: '14:32:26', a: 'Search', cls: 'agent', m: '开始执行：检索 Flask 测试最佳实践…', d: 'Search Agent 生成检索关键词并调用 search/web_search，聚合 Flask + pytest 的组织方式与常见坑。' },
    { t: '14:32:40', a: 'Search', cls: 'agent', m: '完成：已聚合 5 条参考来源', d: '检索完成：聚合 5 条来源（Flask 官方测试文档、pytest fixtures 用法等），要点已写入上下文供 Dev / Test 参考。' }
  ];
  (function () {
    var list = $('demo-log-list'), badge = $('demo-log-badge');
    var toggle = $('demo-log-toggle'), modalOpen = $('demo-log-modal-open');
    var modal = $('demo-log-modal'), modalBody = $('demo-log-modal-body'), modalClose = $('demo-log-modal-close');
    if (!list) return;
    var count = 0;
    function addLine(l, fresh) {
      count++;
      var div = document.createElement('div');
      div.className = 'logline' + (fresh ? ' fresh' : '');
      div.innerHTML = '<span class="lt">' + l.t + '</span><span class="la ' + l.cls + '">' + l.a + '</span><span class="lm">' + l.m + '</span>';
      div.addEventListener('click', function () {
        modalBody.innerHTML = '<div class="meta">[' + l.t + '] [' + l.a + '] ' + l.m + '</div>' + l.d;
        modal.classList.add('open');
      });
      list.appendChild(div);
      list.scrollTop = list.scrollHeight;
      badge.textContent = count + ' 条';
    }
    LOG_INIT.forEach(function (l) { addLine(l, false); });
    var qi = 0;
    var timer = setInterval(function () {
      if (qi >= LOG_QUEUE.length) { clearInterval(timer); return; }
      addLine(LOG_QUEUE[qi], true); qi++;
    }, 1900);
    toggle.addEventListener('click', function () {
      var hidden = list.style.display === 'none';
      list.style.display = hidden ? '' : 'none';
      toggle.textContent = hidden ? '收起' : '展开';
    });
    modalOpen.addEventListener('click', function () {
      var last = LOG_INIT.concat(LOG_QUEUE)[Math.min(count, LOG_INIT.length + LOG_QUEUE.length) - 1] || LOG_INIT[0];
      modalBody.innerHTML = '<div class="meta">[' + last.t + '] [' + last.a + '] ' + last.m + '</div>' + last.d +
        '<div style="margin-top:10px;color:var(--muted);font-size:12px;">提示：点击列表中的任意日志行，可查看该条对应的完整 detail。</div>';
      modal.classList.add('open');
    });
    modalClose.addEventListener('click', function () { modal.classList.remove('open'); });
    modal.addEventListener('click', function (e) { if (e.target === modal) modal.classList.remove('open'); });
  })();

  /* ---------- FR-5 交付结果 ---------- */
  (function () {
    var ok = $('demo-del-ok'), fail = $('demo-del-fail');
    var okP = $('demo-del-ok-panel'), failP = $('demo-del-fail-panel');
    if (!ok) return;
    ok.addEventListener('click', function () {
      okP.classList.add('show'); failP.classList.remove('show');
      ok.classList.add('on-ok'); ok.style.background = 'rgba(16,185,129,.07)';
      fail.classList.remove('on-fail'); fail.style.background = '#fff';
    });
    fail.addEventListener('click', function () {
      failP.classList.add('show'); okP.classList.remove('show');
      fail.classList.add('on-fail'); fail.style.background = 'rgba(239,68,68,.07)';
      ok.classList.remove('on-ok'); ok.style.background = '#fff';
    });
  })();

  /* ---------- FR-6 调度剧本 ---------- */
  (function () {
    var labels = $('demo-sim-labels'), bar = $('demo-sim-bar'), log = $('demo-sim-log');
    var btnA = $('demo-sim-normal'), btnB = $('demo-sim-fail');
    if (!bar) return;
    buildFlow(labels, bar);
    function simLine(t, a, cls, m, sk) {
      var div = document.createElement('div');
      div.className = 'logline' + (sk ? ' skipped' : '');
      div.innerHTML = '<span class="lt">' + t + '</span><span class="la ' + cls + '">' + a + '</span><span class="lm">' + m + '</span>';
      log.appendChild(div); log.scrollTop = log.scrollHeight;
    }
    function tt(n, sec) { var m = n < 10 ? '0' + n : '' + n; return '10:' + m + ':' + sec; }
    async function normal() {
      btnA.disabled = btnB.disabled = true; resetBar(bar); log.innerHTML = '';
      simLine('10:00:01', 'dispatch', 'dispatch', '按 execution_order 调度：t1→t2→t3→t4');
      var seq = ['CEO', 'PM', 'Search', 'Dev', 'Test', 'DevOps', 'Review', 'Analyst', 'Writer', 'Customer'];
      for (var i = 0; i < seq.length; i++) {
        var a = seq[i];
        setSeg(bar, a, 'working'); simLine(tt(i + 2, '00'), a, a === 'CEO' ? 'ceo' : (a === 'Customer' ? 'customer' : 'agent'), a + ' 开始执行…');
        await sleep(340);
        setSeg(bar, a, 'done'); simLine(tt(i + 2, '30'), a, a === 'CEO' ? 'ceo' : (a === 'Customer' ? 'customer' : 'agent'), a + ' 完成');
        await sleep(90);
      }
      simLine('10:13:00', 'Customer', 'customer', '任务完成 · 全部环节正常');
      btnA.disabled = btnB.disabled = false;
    }
    async function failDev() {
      btnA.disabled = btnB.disabled = true; resetBar(bar); log.innerHTML = '';
      simLine('10:00:01', 'dispatch', 'dispatch', '按 execution_order 调度：t1→t2→t3→t4');
      var seq = ['CEO', 'PM', 'Search', 'Dev', 'Test', 'DevOps', 'Review', 'Analyst', 'Writer', 'Customer'];
      for (var i = 0; i < seq.length; i++) {
        var a = seq[i];
        if (a === 'Test' || a === 'Review') {
          setSeg(bar, a, 'skipped');
          simLine(tt(i + 2, '00'), 'dispatch', 'dispatch', a + ' 已跳过 · 依赖 dev 失败', true);
          await sleep(300); continue;
        }
        setSeg(bar, a, 'working');
        simLine(tt(i + 2, '00'), a, a === 'CEO' ? 'ceo' : (a === 'Customer' ? 'customer' : 'agent'), a + ' 开始执行…');
        await sleep(340);
        if (a === 'Dev') {
          setSeg(bar, a, 'error');
          simLine('10:04:30', 'Dev', 'agent', 'Dev 执行失败：LLM 输出解析失败（error）');
          simLine('10:04:31', 'dispatch', 'dispatch', '单点失败不中断 · 后续无依赖子任务继续');
          await sleep(320); continue;
        }
        setSeg(bar, a, 'done');
        simLine(tt(i + 2, '30'), a, a === 'CEO' ? 'ceo' : (a === 'Customer' ? 'customer' : 'agent'), a + ' 完成');
        await sleep(90);
      }
      simLine('10:13:00', 'Customer', 'customer', '整合完成 · 交付说明中标注 Dev 失败环节');
      btnA.disabled = btnB.disabled = false;
    }
    btnA.addEventListener('click', normal);
    btnB.addEventListener('click', failDev);
  })();

  /* ---------- 目录滚动高亮 ---------- */
  (function () {
    var links = Array.prototype.slice.call(document.querySelectorAll('nav.toc a'));
    var map = {};
    links.forEach(function (a) { map[a.getAttribute('href').slice(1)] = a; });
    var targets = Object.keys(map).map(function (id) { return document.getElementById(id); }).filter(Boolean);
    if (!('IntersectionObserver' in window) || !targets.length) return;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          links.forEach(function (a) { a.classList.remove('active'); });
          map[e.target.id].classList.add('active');
        }
      });
    }, { rootMargin: '-15% 0px -70% 0px' });
    targets.forEach(function (t) { io.observe(t); });
  })();
})();
