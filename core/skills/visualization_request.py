"""Recognize requests for a chart artifact without authorizing model training."""
import re


def requests_chart(text):
    text = str(text or '').lower()
    chart = re.search(r'图形|图表|可视化|曲线|趋势图|对比图|残差图|折线图|散点图|画.{0,4}图|\b(?:chart|plot)\b', text)
    boundary = re.search(r'不要|不需要|不用|禁止|无需|别画|如果|假如|假设|引用|原话|这句话|按钮|提示词|怎么|如何|是什么|什么意思|介绍|解释|区别', text)
    request = re.search(r'能.{0,6}(?:给我|帮我|看)|可以.{0,6}(?:给我|帮我|看)|请|帮我|给我|生成|展示|绘制|画|想看|看看|来一张|\b(?:show|plot|create)\b', text)
    return bool(chart and request and not boundary)
