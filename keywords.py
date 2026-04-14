#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
招投标RSS关键词过滤配置
合并三个情报采集的关键词：电力市场/新能源/数据要素/招投标
"""

HIGH_KEYWORDS = [
    # 电力市场核心
    "电力交易", "现货市场", "中长期交易", "虚拟电厂", "独立储能",
    "调峰调频", "辅助服务", "容量补偿", "偏差考核", "节点电价",
    "售电", "电价机制", "市场化改革", "电力市场", "源网荷储",
    "配储", "绿电", "电能量", "新能源参与市场", "电力现货",
    "电力辅助服务", "电力中长期", "电力市场化", "电力改革",
    # 新能源
    "光伏招标", "风电招标", "储能招标", "充电桩招标", "新能源招标",
    "新能源储能", "分布式光伏", "海上风电", "风电储能",
    # 数据要素
    "数据要素", "数据资产", "数据交易", "可信数据空间", "数据入表",
    "数据基础设施", "数据治理", "公共数据授权运营",
    # 招投标核心词
    "招标公告", "采购公告", "中标公告", "招标采购", "挂网公告",
    "投标邀请", "竞争性磋商", "竞争性谈判", "单一来源采购",
]

MEDIUM_KEYWORDS = [
    "新能源", "光伏", "风电", "储能", "充电桩", "微电网",
    "电力", "电网", "氢能", "碳中和", "新能源装机", "电力设备",
    "电力系统", "输配电", "调度", "配电自动化", "智能电网",
    "综合能源", "能源互联网", "源网荷储", "电力建设",
    "采购", "招标", "中标", "投标", "竞标", "挂网", "公告",
    "数据开放", "数据共享", "数据流通", "数据确权",
]

LOW_KEYWORDS = [
    "能源", "碳", "lng", "天然气", "核电", "氨", "油气", "煤炭",
    "石油", "化工", "水利", "水电",
]


def relevance_score(title: str, summary: str = "") -> str:
    """判断内容与目标的关联度"""
    text = (title + " " + summary).lower()
    for kw in HIGH_KEYWORDS:
        if kw.lower() in text:
            return "HIGH"
    for kw in MEDIUM_KEYWORDS:
        if kw.lower() in text:
            return "MEDIUM"
    for kw in LOW_KEYWORDS:
        if kw.lower() in text:
            return "LOW"
    return "NONE"


def passes_filter(title: str, summary: str = "") -> bool:
    """判断内容是否通过关键词过滤（MEDIUM及以上通过）"""
    score = relevance_score(title, summary)
    return score in ("HIGH", "MEDIUM")
