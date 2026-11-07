# 周刊虚拟歌手中文曲排行榜 → RSS

把 [evocalrank.com](https://www.evocalrank.com/) 的周刊（当期 + 历史）自动转成公开 RSS 源。
纯 GitHub 免费方案：**Actions 定时抓取 → 生成 feed.xml → Pages 对外提供订阅**。

## 原理

该站是纯静态 SPA，全部内容来自公开 JSON（无接口鉴权、无爬虫需求）：

| 数据 | 地址 |
|---|---|
| 当期周刊 | `https://www.evocalrank.com/data/info/latest.json` |
| 历史周刊目录 | `https://www.evocalrank.com/data/info/info.json` |
| 单期数据 | `https://www.evocalrank.com/data/rank_data/{期号}.json` |

本仓库用 Python 脚本（仅标准库）拉取 JSON 并生成 RSS 2.0，每期一条 item：
主榜 TOP10 + 超神曲 + 本期推荐 + 统计摘要，歌名直链 B 站视频。

## 部署（已完成的现成部署）

本仓库已部署好，无需手动操作：

1. 代码推送到 `main` 后，Actions 自动跑 `Update RSS feed`。
2. 工作流生成 `feed.xml` → 提交回仓库留档 → 打包上传并部署到 GitHub Pages。
3. 仓库 Settings → Pages → Source 为 `GitHub Actions`。
4. 之后每天北京时间 09:00 自动刷新，订阅地址永远不变。

**订阅地址**：`https://aursxos-vibe.github.io/evocalrank-rss/feed.xml`

> 因为用 `GitHub Actions` 作为 Pages 源，每次工作流运行都会重新部署站点，
> 所以 feed 更新是确定性的，不依赖「分支推送触发 Pages 重建」的时序。

### 从零复刻

```bash
git init && git add . && git commit -m "init"
git remote add origin https://github.com/<用户名>/evocalrank-rss.git
git branch -M main && git push -u origin main
```
然后在仓库 Settings → Pages → Source 选 `GitHub Actions`，手动跑一次工作流即可。

## 本地运行

```bash
python3 evocalrank2rss.py -n 20 -o feed.xml   # 最近20期
python3 evocalrank2rss.py --latest-only       # 只抓当期，最快
python3 evocalrank2rss.py -n 0                # 全部历史 224 期
```

## 说明与注意

- GitHub Actions 定时任务在高峰期可能延迟十几分钟到几小时，对周更内容无影响。
- Pages 返回的 Content-Type 是 `application/xml`，几乎所有 RSS 阅读器都能正常识别。
- 若仓库 60 天无任何活动，Actions 会暂停定时。本工作流每次运行都会把 `feed.xml`
  （含 `lastBuildDate`）提交回仓库，相当于每天一次心跳，可稳定规避这个限制；
  代价是提交历史里会每天多一条 `chore: update RSS feed`。若嫌吵，可把脚本里的
  `lastBuildDate` 改成固定值或删掉「Commit feed if changed」步骤。
- 数据与榜单归 evocalrank 组委会所有，本工具仅作个人/公众聚合阅读订阅，条目内均附官网与 B 站原链，请保留出处。
