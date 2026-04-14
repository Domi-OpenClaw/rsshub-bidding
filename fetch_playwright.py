#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
招投标采集脚本 - Playwright浏览器自动化版
通过Playwright模拟浏览器，抓取动态加载的招标公告列表
"""
import sys
import time
import json
from datetime import datetime, timezone
from pathlib import Path

# 导入关键词过滤
from keywords import passes_filter

def fetch_with_playwright():
    """用Playwright抓取动态页面"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright未安装，尝试安装...", file=sys.stderr)
        import subprocess
        result = subprocess.run(
            ["pip", "install", "playwright", "-q"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            print(f"安装失败: {result.stderr}", file=sys.stderr)
            return []
        # 安装浏览器
        subprocess.run(["playwright", "install", "chromium", "--with-deps"], 
                      capture_output=True, timeout=120)
        from playwright.sync_api import sync_playwright

    entries = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            '--no-sandbox', '--disable-dev-shm-usage', 
            '--disable-setuid-sandbox', '--disable-gpu'
        ])
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
            extra_http_headers={'Accept-Language': 'zh-CN,zh;q=0.9'}
        )
        page = context.new_page()
        page.set_default_timeout(30000)

        # ---------- 来源1: 中国采购与招标网 招标公告列表 ----------
        try:
            print("  🌐 抓取 中国采购与招标网 (chinabidding.cn/zbgg/)...", end=" ", flush=True)
            page.goto("https://www.chinabidding.cn/zbgg/", wait_until="networkidle", timeout=20000)
            # 等待列表加载
            page.wait_for_timeout(3000)

            # 提取所有招标公告链接
            links = page.query_selector_all("a[href*='/zbgg/'], a[href*='/zfcg/'], a[href*='/xmxx/']")
            count = 0
            for a in links:
                text = a.inner_text().strip()
                href = a.get_attribute('href') or ''
                if text and len(text) >= 10 and passes_filter(text):
                    # 构造完整URL
                    if href.startswith('http'):
                        full_url = href
                    elif href.startswith('/'):
                        full_url = 'https://www.chinabidding.cn' + href
                    else:
                        full_url = 'https://www.chinabidding.cn/' + href
                    
                    # 从URL提日期
                    import re
                    date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', href)
                    date_str = datetime.now().strftime('%Y-%m-%d')
                    if date_match:
                        date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"

                    entries.append({
                        "title": text,
                        "link": full_url,
                        "summary": "",
                        "updated": date_str,
                        "source": "chinabidding",
                    })
                    count += 1
            print(f"{count} 条")
        except Exception as e:
            print(f"失败: {e}")

        # ---------- 来源2: 中国采购与招标网 政府招标列表 ----------
        try:
            print("  🌐 抓取 中国采购与招标网 政府招标 (chinabidding.cn/zfcg/)...", end=" ", flush=True)
            page.goto("https://www.chinabidding.cn/zfcg/", wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(3000)

            links = page.query_selector_all("a[href*='/zfcg/'], a[href*='/zbgg/']")
            count = 0
            for a in links:
                text = a.inner_text().strip()
                href = a.get_attribute('href') or ''
                if text and len(text) >= 10 and passes_filter(text):
                    if href.startswith('http'):
                        full_url = href
                    elif href.startswith('/'):
                        full_url = 'https://www.chinabidding.cn' + href
                    else:
                        full_url = 'https://www.chinabidding.cn/' + href

                    import re
                    date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', href)
                    date_str = datetime.now().strftime('%Y-%m-%d')
                    if date_match:
                        date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"

                    entries.append({
                        "title": text,
                        "link": full_url,
                        "summary": "",
                        "updated": date_str,
                        "source": "chinabidding_zfcg",
                    })
                    count += 1
            print(f"{count} 条")
        except Exception as e:
            print(f"失败: {e}")

        context.close()
        browser.close()

    # 去重
    seen = set()
    unique = []
    for e in entries:
        if e["link"] not in seen:
            seen.add(e["link"])
            unique.append(e)

    return unique


def build_rss(entries: list, output_path: str):
    """构建RSS XML"""
    seen = set()
    unique = []
    for e in entries:
        if e["link"] and e["link"] not in seen:
            seen.add(e["link"])
            unique.append(e)

    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    items_xml = ""
    for e in unique[:50]:
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
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始抓取（Playwright模式）...")

    entries = fetch_with_playwright()
    print(f"共获取 {len(entries)} 条（去重前）")

    # 去重
    seen = set()
    unique = []
    for e in entries:
        if e["link"] not in seen:
            seen.add(e["link"])
            unique.append(e)

    print(f"去重后 {len(unique)} 条")

    count = build_rss(unique, output)
    print(f"RSS生成完成: {output} ({count} 条)")

    if unique:
        print("\n最新5条：")
        for e in unique[:5]:
            print(f"  [{e['updated']}] {e['title'][:60]}")

    return count


if __name__ == "__main__":
    sys.exit(0 if main() > 0 else 1)
