from django.shortcuts import render


def dashboard(request):
    context = {
        "board_name": "美本申请总控台",
        "stats": [
            {"label": "目标学校", "value": 18},
            {"label": "已提交申请", "value": 6},
            {"label": "待提交文书", "value": 9},
            {"label": "本周DDL", "value": 4},
        ],
        "tasks": [
            {"title": "Common App 主文书二稿", "owner": "你", "deadline": "2026-05-10", "priority": "高", "status": "进行中"},
            {"title": "哥大补充文书 - Why Columbia", "owner": "文书老师", "deadline": "2026-05-12", "priority": "中", "status": "待开始"},
            {"title": "更新活动列表（10项）", "owner": "你", "deadline": "2026-05-06", "priority": "高", "status": "复核中"},
            {"title": "MIT 推荐信跟进", "owner": "家长", "deadline": "2026-05-08", "priority": "中", "status": "待反馈"},
        ],
    }
    return render(request, 'dashboard.html', context)
