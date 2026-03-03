# HZdealMap

杭州楼盘成交可视化示例：展示杭州版图，鼠标悬浮地图时自动显示当前位置附近楼盘的成交信息（当月、当季、当年）。

## 访问方式
- 推荐入口：`http://localhost:8000/`
- 兼容入口：`http://localhost:8000/dashboard.html`（大小写不敏感，如 `dashboard.HTML` 也可）

## 现在不是“纯静态页面”
- 首页由服务端动态渲染（把数据库中的初始楼盘和汇总数据注入 HTML）
- 页面加载后继续通过 API 轮询最新汇总与楼盘点位
- 鼠标移动时实时按坐标查询最近楼盘并高亮

## 功能
- 杭州区域地图展示（含简化边界叠加）
- 鼠标悬浮联动：显示最近楼盘成交数据
- 地图点位高亮：当前楼盘自动突出显示
- 汇总面板动态刷新：楼盘数量、月/季/年总成交、更新时间
- 信息源接入：
  - 默认读取本地 `data/source_sample.json`
  - 支持 `POST /api/sync-source` 从远程 JSON 源拉取刷新

## 数据源格式
远程 JSON 或本地 JSON 需包含：

```json
{
  "projects": [
    {
      "name": "楼盘名",
      "district": "区名",
      "lat": 30.27,
      "lng": 120.15,
      "monthly_deals": 12,
      "quarterly_deals": 34,
      "yearly_deals": 120
    }
  ]
}
```

## 运行
```bash
python app.py
```

打开 `http://localhost:8000`。

## API
- `GET /api/projects?lat=<float>&lng=<float>`：查询位置最近楼盘
- `GET /api/projects/all`：获取所有楼盘用于地图渲染
- `GET /api/summary`：获取动态汇总数据
- `POST /api/sync-source`：同步数据源
  - Body(JSON): `{"source_url": "https://your-domain/data.json"}`
  - 或设置环境变量 `HZ_SOURCE_URL`

## 常见问题
- GitHub 看不到文件：说明本地提交还没有推送到远端分支（`git push`）或你查看的是另一个仓库/分支。
- 打开 `dashboard.HTML` 报错：旧版本只支持 `/`，当前版本已兼容 `/dashboard.html` / `/dashboard.HTML`。
