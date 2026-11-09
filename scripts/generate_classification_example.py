"""Produce explicit, synthetic educational topic labels; never infer labels from inputs."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
samples = {
    "mathematics": ["求三角形面积时要测量底和高", "分数的分子和分母分别表示什么", "计算长方形的周长需要哪些数据", "如何比较两个小数的大小", "方程两边同时加一会发生什么", "把一组数相加再除以个数得到平均数", "质数只有两个正整数因数", "用坐标描述平面上的一个点", "求圆的面积需要知道半径", "比和比例可以描述数量之间的关系", "如何判断一个整数能被三整除", "百分数可以表示整体中的比例", "直角三角形的两条直角边", "图表中的中位数如何确定", "负数和正数在数轴上的位置", "多边形可以按边数进行分类", "列竖式计算多位数乘法", "概率用于描述随机事件发生的可能性"],
    "language": ["找出句子中表示动作的词语", "阅读文章后概括段落的中心意思", "用标点符号区分陈述句和疑问句", "词典可以帮助理解生词的含义", "写作文前先列出文章的提纲", "找出一段文字中的比喻表达", "修改句子中的错别字和语病", "古诗朗读时注意节奏和停顿", "用自己的话复述故事内容", "根据上下文理解一个词的意思", "学习英语名词的单数与复数", "用完整的句子回答阅读问题", "查找文章中的时间地点和人物", "用连接词使段落表达更连贯", "观察汉字的偏旁并了解字义", "将直接引语改写成转述句", "比较两篇文章描写景物的方法", "写信时要注意称呼和落款"],
    "science": ["植物利用光能进行光合作用", "观察水在加热过程中的蒸发现象", "地球绕太阳运行形成一年的周期", "磁铁可以吸引某些金属", "声音需要介质才能传播", "比较不同材料的导热速度", "观察种子发芽需要的水和空气", "记录月亮在一个月中的形状变化", "用温度计测量水的冷热程度", "研究影子长度随太阳位置的变化", "动物通过呼吸获得生命活动所需的氧气", "物体下落受到地球引力影响", "通过过滤分离水中的不溶性杂质", "电路接通后小灯泡才能发光", "了解食物链中生产者和消费者", "风是空气流动产生的自然现象", "比较固体液体和气体的性质", "实验前佩戴护目镜并遵守安全规则"],
}
rows = []
for label, texts in samples.items():
    for text in texts:
        rows.append({"sample_id": f"CLASS-{len(rows)+1:03d}", "instruction": text, "output": label,
                     "classification_label": label, "task_type": "text_classification"})
payload = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows).encode("utf-8")
target = ROOT / "demo-datasets/education-classification-synthetic.jsonl"
target.write_bytes(payload)
target.with_suffix(".sha256").write_text(hashlib.sha256(payload).hexdigest() + "\n", encoding="ascii")
print(f"Synthetic labeled records: {len(rows)}; labels: {', '.join(samples)}")
