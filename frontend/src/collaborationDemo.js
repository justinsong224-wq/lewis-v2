export const collaborationDemo = [
  { role: 'pm', title: '需求分析', message: '明确 CSV 批量预测与下载范围', seconds: 4 },
  { role: 'search', title: '技术调研', message: '查找 CSV 解析与下载的实现依据', seconds: 4 },
  { role: 'ceo', title: '技术规划', message: '安排开发、测试、文档和审查', seconds: 4 },
  { role: 'dev', title: '开发实现', message: '在已有短信项目上增加批量接口和页面', seconds: 6 },
  { role: 'test', title: '测试验证', message: '演示单条回归、批量预测与输入校验环节', seconds: 4 },
  { role: 'writer', title: '编写文档', message: '整理启动方式与 CSV 使用说明', seconds: 3 },
  { role: 'review', title: '代码审查', message: '检查需求覆盖与实现问题', seconds: 4 },
  { role: 'customer', title: '整理交付', message: '说明文件、验证结果和交付范围', seconds: 3 },
]
export const collaborationDemoSeconds = collaborationDemo.reduce((sum, stage) => sum + stage.seconds, 0)
