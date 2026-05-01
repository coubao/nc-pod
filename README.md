# 美本申请项目管理工具（Django）

一个可在 macOS 上直接运行的 Django Web 应用，界面和交互风格参考 Notion，聚焦美本申请全流程管理。

## 功能亮点

- 申请总览 Dashboard（关键指标卡片）
- Notion 风格任务表格（支持前端快速新增与行内编辑）
- 学校/文书/材料模块导航（可继续扩展为独立页面）
- 响应式布局，适配桌面与平板

## 本地运行（macOS）

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

浏览器打开：`http://127.0.0.1:8000/`

## 下一步建议

- 接入 Django Model 实现任务持久化
- 增加拖拽看板（To do / Doing / Done）
- 增加登录权限（学生/家长/顾问）
- 对接日历与邮件提醒
