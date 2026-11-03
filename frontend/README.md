# Lewis 前端

Vue 3 + Vite + Pinia + Element Plus

## 本地启动

```bash
npm install   # 已提前装好，正常无需重复执行
npm run dev
```

默认运行在 http://localhost:5173

## 前置条件

后端必须已经在 http://127.0.0.1:8000 启动（参考 backend/run.sh），
否则任务提交和 WebSocket 连接会失败。

## 目录结构

```
src/
├── App.vue                 # 整体布局（顶栏 + 办公室场景 + 侧边栏）
├── stores/
│   └── taskStore.js         # Pinia store：任务状态、WebSocket 连接
└── components/
    ├── TaskInput.vue         # 任务输入框
    ├── OfficeScene.vue        # 按部门分组的工位区
    ├── DigitalEmployee.vue    # 单个数字员工卡片
    ├── TaskFlow.vue           # 任务进度时间线
    └── ExecutionLog.vue       # 实时执行日志（终端风格）
```

## 已知限制

- 字体使用 Google Fonts CDN（JetBrains Mono），无网络时会自动降级到系统等宽字体
- WebSocket 地址硬编码为 `ws://127.0.0.1:8000`，部署到其他环境需要修改 `stores/taskStore.js` 里的 `API_BASE`