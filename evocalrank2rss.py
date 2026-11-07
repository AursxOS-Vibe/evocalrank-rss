#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evocalrank2rss —— 周刊虚拟歌手中文曲排行榜(evocalrank.com) → RSS 2.0 转换器

原理：该站是纯静态 SPA，全部数据来自公开 JSON 文件：
  - 目录索引:  https://www.evocalrank.com/data/info/info.json   (历史周刊列表)
  - 当期数据:  https://www.evocalrank.com/data/info/latest.json
  - 单期数据:  https://www.evocalrank.com/data/rank_data/{期号}.json

用法：
  python3 evocalrank2rss.py                 # 默认生成最近 10 期的 RSS
  python3 evocalrank2rss.py -n 30           # 生成最近 30 期
  python3 evocalrank2rss.py -n 0            # 全部历史期数(224期，较慢)
  python3 evocalrank2rss.py -o feed.xml     # 指定输出文件
  python3 evocalrank2rss.py --latest-only   # 只读 latest.json，最快，适合高频定时更新

配合 cron / RSS Reader 示例（每天 12:00 更新一次）：
  0 12 * * * cd /path/to/dir && python3 evocalrank2rss.py -n 10 -o feed.xml
  然后把 feed.xml 通过任意静态托管(GitHub Pages / NAS / 本地 http server)暴露为 URL，
  或直接以本地文件形式加入支持本地文件的 RSS 阅读器。

仅依赖 Python3 标准库。
"""
import argparse
import json
import sys
import time
import urllib.request
from email.utils import format_datetime
from datetime import datetime, timezone, timedelta
from html import escape
from xml.sax.saxutils import escape as xml_escape

BASE = "https://www.evocalrank.com"
INFO_URL = f"{BASE}/data/info/info.json"
LATEST_URL = f"{BASE}/data/info/latest.json"
RANK_URL = BASE + "/data/rank_data/{}.json"
UA = "Mozilla/5.0 (compatible; evocalrank2rss/1.0; personal RSS reader)"
CST = timezone(timedelta(hours=8))


def http_get_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))


def norm_pubdate(v):
    """兼容新旧格式：pubdate 可能是 str、list 或缺失。返回 datetime 或 None。"""
    if isinstance(v, list) and v:
        v = v[0]
    if not isinstance(v, str):
        return None
    try:
        dt = datetime.strptime(v.strip(), "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=CST)
    except ValueError:
        return None


def fmt_int(n):
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return "-"


def song_line(item):
    """生成单曲一行 HTML。"""
    title = escape(item.get("title") or "(无题)")
    url = item.get("url") or "#"
    point = fmt_int(item.get("point"))
    play = fmt_int(item.get("play"))
    rank = item.get("rank")
    rank_txt = f"{rank}. " if isinstance(rank, int) else ""
    return (f'<div class="song">{rank_txt}<a href="{url}">{title}</a>'
            f'　<i>综合index {point}｜播放 {play}</i></div>')


def build_item_html(d):
    parts = [f'<p>统计区间：{escape(str(d.get("collect_start_time","?")))} ~ '
             f'{escape(str(d.get("collect_end_time","?")))}</p>']

    main = d.get("main_rank") or []
    parts.append(f'<h3>主榜 TOP {min(10, len(main)) if main else 0}</h3>')
    for m in main[:10]:
        parts.append(song_line(m))
    if len(main) > 10:
        parts.append(f'<p>……主榜共 {len(main)} 首，完整榜单见'
                     f'<a href="{BASE}/#/{ "normal/" + str(d.get("ranknum")) }">官网本期页</a></p>')

    sup = d.get("super_hit") or []
    if sup:
        parts.append('<h3>超神曲</h3>')
        for s in sup:
            parts.append(song_line(s))

    pick = d.get("pick_up") or []
    if pick:
        parts.append('<h3>本期推荐</h3>')
        for s in pick:
            parts.append(song_line(s))

    st = d.get("statistic") or {}
    if isinstance(st, dict) and st:
        parts.append(
            f'<p><i>本期收录新增 {fmt_int(st.get("new_video_count"))} 首｜'
            f'入榜新曲 {fmt_int(st.get("new_in_rank_count"))} 首｜'
            f'主榜新曲 {fmt_int(st.get("new_in_mainrank_count"))} 首</i></p>')
    return "\n".join(parts)


def build_feed(issues, title, desc, site_url):
    items_xml = []
    for d in issues:
        num = d.get("ranknum")
        dt = norm_pubdate(d.get("pubdate")) or datetime.now(CST)
        link = f"{site_url}/#/normal/{num}"
        html = build_item_html(d)
        html = ('<style>.song{margin:2px 0}</style>'
                f'<p><a href="{link}">▶ 第 {num} 期 · 在官网查看完整榜单</a></p>' + html)
        items_xml.append(
            "    <item>\n"
            f"      <title>{xml_escape(f'周刊虚拟歌手中文曲排行榜 第{num}期')}</title>\n"
            f"      <link>{link}</link>\n"
            f"      <guid isPermaLink=\"false\">evocalrank-{num}</guid>\n"
            f"      <pubDate>{format_datetime(dt)}</pubDate>\n"
            f"      <description><![CDATA[{html}]]></description>\n"
            "    </item>")
    now = format_datetime(datetime.now(CST))
    newest_dt = norm_pubdate(issues[0].get("pubdate")) if issues else None
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>{xml_escape(title)}</title>\n"
        f"    <link>{site_url}</link>\n"
        f"    <description>{xml_escape(desc)}</description>\n"
        "    <language>zh-CN</language>\n"
        f"    <lastBuildDate>{now}</lastBuildDate>\n"
        f"    <pubDate>{format_datetime(newest_dt) if newest_dt else now}</pubDate>\n"
        f"    <image><url>{site_url}/favicon.ico</url><title>{xml_escape(title)}</title>"
        f"<link>{site_url}</link></image>\n"
        + "\n".join(items_xml) + "\n"
        "  </channel>\n</rss>\n")


def main():
    ap = argparse.ArgumentParser(description="evocalrank.com → RSS 转换器")
    ap.add_argument("-n", "--num", type=int, default=10,
                    help="收录最近期数，0=全部（默认10）")
    ap.add_argument("-o", "--output", default="feed.xml", help="输出 XML 文件")
    ap.add_argument("--latest-only", action="store_true",
                    help="只抓 latest.json（单条最新期，速度最快）")
    args = ap.parse_args()

    issues = []
    if args.latest_only:
        issues = [http_get_json(LATEST_URL)]
        print("模式：仅当期 latest.json")
    else:
        info = http_get_json(INFO_URL)
        rank_list = info.get("rank_list") or []
        # 目录里 url 字段本身就是绝对地址，直接复用
        targets = rank_list if args.num == 0 else rank_list[: args.num]
        print(f"共 {len(rank_list)} 期历史，本次抓取 {len(targets)} 期 ...")
        for i, t in enumerate(targets):
            url = t.get("url") or RANK_URL.format(t.get("rank_num"))
            try:
                d = http_get_json(url)
                issues.append(d)
                print(f"  [{i+1}/{len(targets)}] 第{d.get('ranknum')}期  ok")
            except Exception as e:
                print(f"  [{i+1}/{len(targets)}] 期号{t.get('rank_num')}  失败: {e}",
                      file=sys.stderr)
            time.sleep(0.3)  # 温和限速，避免给静态站造成压力

    if not issues:
        print("没有取到任何数据，退出。", file=sys.stderr)
        sys.exit(1)

    xml = build_feed(
        issues,
        "周刊虚拟歌手中文曲排行榜",
        "周刊虚拟歌手中文曲排行榜（evocalrank.com）RSS，由本地脚本定时生成。",
        BASE)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"完成：{len(issues)} 期 → {args.output}")


if __name__ == "__main__":
    main()
