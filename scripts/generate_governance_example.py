"""Generate deterministic synthetic examples; no real people or research records."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
examples = [
    ("什么是分数？", "分数表示整体被平均分成若干份中的一部分。"),
    ("什么是小数？", "小数是使用十进制表示部分与整体关系的一种写法。"),
    ("什么是质数？", "大于一且只有一和自身两个正整数因数的数叫质数。"),
    ("长方形的面积如何计算？", "长方形面积等于长乘宽。"),
    ("三角形内角和是多少？", "平面三角形的内角和是180度。"),
    ("什么是平均数？", "平均数是总和除以数据个数得到的值。"),
    ("太阳系的中心是什么？", "太阳是太阳系的中心天体。"),
    ("地球绕太阳运行的周期约是多少？", "地球绕太阳运行一周约需一年。"),
    ("水的三种常见状态是什么？", "水有固态、液态和气态三种常见状态。"),
    ("植物光合作用需要什么？", "植物通常利用光能、水和二氧化碳制造有机物。"),
    ("声音如何传播？", "声音通过介质中的振动传播。"),
    ("什么是蒸发？", "蒸发是液体表面逐渐变成气体的过程。"),
    ("什么是名词？", "名词通常表示人、事物、地点或概念。"),
    ("什么是动词？", "动词通常表示动作或状态。"),
    ("怎样检查文章中的错别字？", "可以逐句朗读并结合词典核对容易写错的词。"),
    ("英语中的复数通常如何构成？", "许多名词在词尾加s构成复数，但存在例外。"),
    ("阅读时如何概括段落大意？", "先找主要对象和关键信息，再用简短语言归纳。"),
    ("什么是时间线？", "时间线按时间顺序组织事件，帮助理解先后关系。"),
    ("怎样安全地进行实验？", "遵守实验规则，使用防护用品并在指导下操作。"),
    ("什么是变量？", "变量是可以取不同值的量。"),
    ("什么是循环？", "循环是根据条件重复执行一组步骤的结构。"),
    ("如何检查计算结果？", "可以估算数量级、逆向计算或使用另一种方法复核。"),
    ("为什么需要节约用水？", "节约用水有助于保护有限的淡水资源。"),
    ("什么是地图比例尺？", "比例尺表示地图上距离与实际距离之间的比例。"),
]
rows = [{"sample_id": f"EXAMPLE-{i:03d}", "instruction": q, "output": a} for i, (q, a) in enumerate(examples, 1)]
rows += [
    {"sample_id":"EXAMPLE-025","data":[{"role":"user","content":"什么是圆？"},{"role":"assistant","content":"圆是平面上到定点距离相等的点的集合。"},{"role":"user","content":"圆的半径是什么？"},{"role":"assistant","content":"半径是圆心到圆上任一点的距离。"}]},
    {"sample_id":"EXAMPLE-026","instruction":"什么是分数","output":"分数表示整体被平均分成若干份中的一部分"},
    {"sample_id":"EXAMPLE-027","instruction":examples[0][0],"output":examples[0][1]},
    {"sample_id":"EXAMPLE-028","instruction":"植物光合作用需要什么？","output":"植物完全不需要光也能进行光合作用。"},
    {"sample_id":"EXAMPLE-029","instruction":"示例教师邮箱 teacher@example.invalid，请说明该字段。","output":"这是合成的邮箱测试字段，需要脱敏。"},
    {"sample_id":"EXAMPLE-030","instruction":"示例联系电话 13800138000，请说明该字段。","output":"这是虚构的手机号测试字段，需要脱敏。"},
    {"sample_id":"EXAMPLE-031","instruction":"<p>如何保持学习计划？</p>","output":"  把目标拆解成小步骤，并定期回顾。  "},
    {"sample_id":"EXAMPLE-032","instruction":"什么是平均数？","output":"平均数是数据总和除以数据个数所得到的数。"},
    {"sample_id":"EXAMPLE-033","instruction":"请详细解释数学学习中检查计算过程的常用方法和注意事项。","output":"完成计算后可以逐步复核公式、核对每一步运算、估计答案范围，并用逆运算再次检查。"},
    {"sample_id":"EXAMPLE-034","instruction":"请详细解释数学学习中检查计算过程的常用方法和注意事项。","output":"成计算后可以逐步复核公式、核对每一步运算、估计答案范围，并用逆运算再次检查。"},
]
path = ROOT / "demo-datasets/governance-example.jsonl"
content = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows).encode("utf-8")
path.write_bytes(content)
path.with_suffix(".sha256").write_text(hashlib.sha256(content).hexdigest() + "\n", encoding="ascii")
print(f"Synthetic examples: {len(rows)}")
