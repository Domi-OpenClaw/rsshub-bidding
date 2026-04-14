#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
招投标采集脚本 - chinabidding.com.cn 版
通过 Playwright 访问 chinabidding.com.cn 首页，点击招标公告链接
"""
import sys
import time
import re
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

# 导入关键词过滤
from keywords import passes_filter

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def fetch_with_playwright():
    """用 Playwright 抓取 chinabidding.com.cn"""
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

        try:
            # 访问首页
            print("🌐 访问 chinabidding.com.cn 首页...", end=" ", flush=True)
            page.goto("https://www.chinabidding.com.cn/", wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(3000)
            print("✓")

            # 查找所有招标相关链接
            print("🔍 筛选招标公告链接...", end=" ", flush=True)
            links = page.query_selector_all("a[href*='/zbgg/'], a[href*='/zfcg/'], a[href*='/xmxx/']")
            print(f"✓ 找到 {len(links)} 个链接")

            count = 0
            for a in links:
                text = a.inner_text().strip()
                href = a.get_attribute('href') or ''

                # 过滤
                if not text or len(text) < 10:
                    continue
                if not passes_filter(text):
                    continue

                # 跳过噪音链接
                skip_keywords = ['关于我们', '联系我们', '网站地图', '加入收藏', '法律声明',
                                  '版权所有', '京ICP备', '帮助中心', '意见反馈', '更多', '>>']
                if any(k in text for k in skip_keywords):
                    continue

                # 构造完整URL
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('/'):
                    full_url = 'https://www.chinabidding.com.cn' + href
                else:
                    full_url = 'https://www.chinabidding.com.cn/' + href

                # 从URL提日期
                date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', href)
                date_str = datetime.now().strftime('%Y-%m-%d')
                if date_match:
                    date_str = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"

                entries.append({
                    "title": text,
                    "link": full_url,
                    "summary": "",
                    "updated": date_str,
                    "source": "chinabidding_com",
                })
                count += 1

            print(f"✓ 过滤后 {count} 条")

        except Exception as e:
            print(f"✗ 错误: {e}")
            import traceback
            traceback.print_exc()

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
    """构建 RSS"""
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
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始抓取（chinabidding.com.cn）...")

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
    print(f"RSS 生成完成: {output} ({count} 条)")

    if unique:
        print("\n最新 5 条：")
        for e in unique[:5]:
            print(f"  [{e['updated']}] {e['title'][:60]}")

    return count


if __name__ == "__main__":
    sys.exit(0 if main() > 0 else 1)
