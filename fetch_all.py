#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
招投标RSS采集脚本
抓取10个RSS源，按关键词过滤，输出RSS XML
"""
import json
import re
import sys
import time
import feedparser
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# 导入关键词过滤
from keywords import passes_filter, relevance_score


SOURCES = [
    # 政府采购
    {
        "id": "ccgp",
        "name": "中国政府采购网",
        "url": "http://www.ccgp.gov.cn/offer/static/zbgg.xml",
        "category": "government",
    },
    # 中招采购
    {
        "id": "cebpubservice",
        "name": "中招联合",
        "url": "https://www.cebpubservice.com/cotb-freeprobe/interact bidding hall/getDataByIdNew?id=zbgg&pageSize=200&pageNum=1&dateRange=30&province=&categoryId=&keyword=&searchkeyword=",
        "category": "government",
    },
    # 千里马
    {
        "id": "qianlima",
        "name": "千里马",
        "url": "https://www.qianlima.com/zb/_downloadxml",
        "category": "bidding",
    },
    # 电力招标
    {
        "id": "dlzb",
        "name": "电力招标网",
        "url": "http://www.dlzb.net/dlzb/",
        "category": "energy",
    },
    # 国家能源局
    {
        "id": "nea",
        "name": "国家能源局",
        "url": "https://rsshub.app/nea/zbxx",
        "category": "government",
    },
    # 国网
    {
        "id": "sgcc",
        "name": "国家电网",
        "url": "https://ecp.sgcc.com.cn/html/index.html",
        "category": "energy",
    },
    # 南网
    {
        "id": "csg",
        "name": "南方电网",
        "url": "https://www.csg.cn/zbgg/",
        "category": "energy",
    },
]


def fetch_rss(url: str, source_id: str) -> list:
    """抓取单个RSS源，返回条目列表"""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; rsshub-bidding/1.0; +https://github.com/Domi-OpenClaw/rsshub-bidding)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=15) as resp:
            content = resp.read()
            # 尝试多种编码
            for enc in ("utf-8", "gbk", "gb2312", "latin1"):
                try:
                    text = content.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            return parse_rss_content(text, source_id)
    except HTTPError as e:
        print(f"  [{source_id}] HTTP {e.code}: {url}", file=sys.stderr)
    except URLError as e:
        print(f"  [{source_id}] URL错误: {e.reason}", file=sys.stderr)
    except Exception as e:
        print(f"  [{source_id}] 解析错误: {e}", file=sys.stderr)
    return []


def parse_rss_content(content: str, source_id: str) -> list:
    """解析RSS内容"""
    entries = []
    try:
        feed = feedparser.parse(content)
        for entry in feed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")
            # 清理HTML
            summary = re.sub(r"<[^>]+>", "", summary)
            updated = entry.get("updated", "") or entry.get("published", "")
            entries.append({
                "title": title,
                "link": link,
                "summary": summary[:500],
                "updated": updated,
                "source": source_id,
            })
    except Exception as e:
        print(f"  [{source_id}] feedparser错误: {e}", file=sys.stderr)
    return entries


def fetch_direct(url: str, source_id: str, name: str) -> list:
    """直接抓取非RSS页面（用于国网、南网等）"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=15) as resp:
            content = resp.read()
            for enc in ("utf-8", "gbk", "gb2312"):
                try:
                    text = content.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            return extract_links(text, source_id, name)
    except Exception as e:
        print(f"  [{source_id}] 直接抓取错误: {e}", file=sys.stderr)
    return []


def extract_links(html: str, source_id: str, source_name: str) -> list:
    """从HTML中提取招标公告链接"""
    entries = []
    # 简单正则提取链接（实际使用时需要针对每个网站单独写解析逻辑）
    pattern = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*招标[^<]*|[^<]*采购[^<]*|[^<]*中标[^<]*)</a>', re.IGNORECASE)
    for match in pattern.finditer(html):
        url = match.group(1)
        title = match.group(2).strip()
        if passes_filter(title):
            entries.append({
                "title": title,
                "link": url if url.startswith("http") else f"https://{url}",
                "summary": "",
                "updated": datetime.now(timezone.utc).isoformat(),
                "source": source_id,
            })
    return entries


def build_rss(entries: list, output_path: str):
    """构建RSS XML文件"""
    # 去重（按link）
    seen = set()
    unique = []
    for e in entries:
        if e["link"] and e["link"] not in seen:
            seen.add(e["link"])
            unique.append(e)

    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    items_xml = ""
    for e in unique:
        pub_date = e.get("updated", now)
        title = e["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        link = e["link"].replace("&", "&amp;")
        desc = e.get("summary", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        items_xml += f"""
    <item>
      <title>{title}</title>
      <link>{link}</link>
      <description>{desc}</description>
      <pubDate>{pub_date}</pubDate>
      <source>{e["source"]}</source>
    </item>"""

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>招投标RSS聚合</title>
    <link>https://domi-openclaw.github.io/rsshub-bidding/bidding.xml</link>
    <description>招投标信息聚合，支持电力/新能源/储能/数据要素关键词过滤</description>
    <language>zh-cn</language>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="https://domi-openclaw.github.io/rsshub-bidding/bidding.xml" rel="self" type="application/rss+xml"/>
{items_xml}
  </channel>
</rss>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rss)

    return len(unique)


def main():
    output = "bidding.xml"
    all_entries = []

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始抓取 {len(SOURCES)} 个RSS源...")

    for src in SOURCES:
        print(f"  抓取 {src['name']}...", end=" ", flush=True)
        entries = fetch_rss(src["url"], src["id"])
        print(f"{len(entries)} 条")

        # 关键词过滤
        filtered = [e for e in entries if passes_filter(e["title"], e.get("summary", ""))]
        print(f"    → 过滤后 {len(filtered)} 条（高相关/MEDIUM）")

        all_entries.extend(filtered)

    print(f"\n共获取 {len(all_entries)} 条（过滤后）")

    # 生成RSS
    count = build_rss(all_entries, output)
    print(f"RSS生成完成: {output} ({count} 条)")
    return count


if __name__ == "__main__":
    main()
