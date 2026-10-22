# -*- coding: utf-8 -*-
"""
生成"政务领域合成演示语料"（Schema v1，与任务二 raw_5k.jsonl 同构）。

设计约束：
- 全部为本地合成文本，license=synthetic，无任何真实个人信息 / 真实机构数据。
- 含少量构造的"脏数据 / 假 PII / 重复"，用于演示任务二的清洗、去重、脱敏能力。
- 确定性：固定 SEED，重复运行字节级一致。
- 产出为"原始输入"状态（clean_text==raw_text、masked_text==raw_text、flags 为空），
  即尚未经过任务二治理，与 raw_5k.jsonl 的 raw 态一致。

注意：本文件仅供演示，不冒充任何公开数据集。
"""
import json
import random
from datetime import datetime, timezone, timedelta

SEED = 4471  # 与项目种子约定保持一致
N_ROWS = 300

CATEGORIES = {
    "社保": [
        ("如何查询个人社保缴费记录？",
         "可通过国家社会保险公共服务平台或当地人社APP，实名登录后进入“缴费记录查询”模块，选择起止年月即可查看每月缴费基数与到账状态。"),
        ("灵活就业人员怎样参加职工养老保险？",
         "携带身份证到户籍地或就业地社保经办机构办理参保登记，也可在政务服务网一键申报，按当地缴费档次自主选择按月或按年缴费。"),
        ("异地就医备案后报销比例会变吗？",
         "办理跨省异地就医备案后，住院费用按就医地目录、参保地比例结算，门诊慢特病需先在参保地认定，比例一般不降低。"),
    ],
    "公积金": [
        ("住房公积金提取需要哪些材料？",
         "常见情形需提供身份证、本人银行卡、提取事由证明（如购房合同、租房备案、离职证明）。通过公积金APP上传影像件即可线上办理。"),
        ("公积金贷款额度如何计算？",
         "贷款额度与账户余额、缴存基数、缴存年限相关，通常不超过账户余额的若干倍且受当地最高限额约束，具体以城市公布公式为准。"),
        ("离职后公积金账户怎么处理？",
         "本地户籍可继续封存或由新单位续缴；异地就业可办理转移接续；符合条件（如离退休、出境定居）方可销户提取。"),
    ],
    "营业执照": [
        ("个体工商户营业执照如何线上办理？",
         "登录政务服务网企业开办专区，填写经营场所、经营范围、经营者信息，系统进行智能预审，预审通过后邮寄或窗口领取执照。"),
        ("营业执照经营范围怎么写才规范？",
         "应使用国民经济行业分类表述，涉及许可项目的注明“凭许可证经营”，避免笼统表述导致后续变更。"),
        ("营业执照遗失如何补领？",
         "先在公示系统声明作废，再提交补领申请并附声明截图，审核通过后发放新照，统一社会信用代码不变。"),
    ],
    "户籍办理": [
        ("新生儿落户需要准备什么？",
         "需父母身份证、结婚证、出生医学证明、落户方户口簿。随父或随母自愿，线上提交材料预审后到派出所打印户口簿。"),
        ("市内迁移户口如何办理？",
         "凭合法稳定住所证明（房产证或租赁备案）在迁入地派出所申请，符合条件当场办结，不需回原籍。"),
        ("户口注销的情形有哪些？",
         "主要包括死亡、参军、出国（境）定居等，由本人或监护人持相关证明办理，涉及财产与社保的应先处理完毕。"),
    ],
    "税务": [
        ("小规模纳税人如何申报增值税？",
         "按季申报，季度销售额未超起征点的免征，超过则按征收率填报。可通过电子税务局一键零申报或据实填报。"),
        ("个人所得税专项附加扣除怎么填？",
         "在个税APP填报子女教育、赡养老人、住房贷款利息等扣除项，汇算清缴时自动累计，留存资料备查。"),
        ("发票遗失可以补开吗？",
         "普通发票遗失可凭声明与存根联复印件入账；专用发票遗失需按规定挂失并接受处理，原则上不补开原件。"),
    ],
}

# 构造用的假 PII（明显虚构，仅用于演示脱敏）
FAKE_NAMES = ["张三", "李四", "王五", "赵六"]
FAKE_PHONES = ["13800000000", "13911111111", "13722222222"]
FAKE_ADDR = ["北京市海淀区中关村大街1号", "上海市浦东新区世纪大道100号", "广州市天河区天河路200号"]
FAKE_ID = ["110108199001010000", "310115199202020000"]


def make_base_records():
    recs = []
    pool = []
    for cat, qa_list in CATEGORIES.items():
        for q, a in qa_list:
            pool.append((cat, q, a))
    # 用 pool 反复取样 + 轻微扰动，生成 N_ROWS 条"基本干净"的记录
    rng = random.Random(SEED)
    i = 0
    while len(recs) < N_ROWS - 60:  # 留出 60 条用于注入问题
        cat, q, a = pool[i % len(pool)]
        i += 1
        # 轻微扰动，制造语义不同但同模板的行
        variant = rng.choice(["", "（示例）", "（常见咨询）", "（办事指南）"])
        raw_text = f"问：{q}{variant}\n答：{a}"
        recs.append((cat, raw_text))
    return recs


def build_record(idx, cat, raw_text):
    sample_id = f"gov-{idx:06d}"
    crawl = datetime(2026, 9, 16, 12, 25, 0, tzinfo=timezone(timedelta(hours=8))).isoformat()
    meta = {
        "source_id": "synthetic-gov-v1",
        "source_url": f"https://example.org/synthetic-gov-v1/{idx:06d}",
        "publish_date": None,
        "crawl_time": crawl,
        "license": "synthetic",
        "authorization": "本地合成，无第三方授权约束",
        "domain": "government",
        "file_path": None,
        "category": cat,
    }
    return {
        "sample_id": sample_id,
        "modality": "text",
        "raw_text": raw_text,
        "meta": meta,
        "clean_text": raw_text,   # 原始输入态：尚未清洗
        "masked_text": raw_text,  # 原始输入态：尚未脱敏
        "hash": {"exact": None, "simhash": None},
        "flags": {
            "rule_issues": [],
            "dup_cluster_id": None,
            "dup_role": None,
            "dup_similar_to": None,
            "pii": [],
            "pii_count": 0,
            "mask_consistent": True,
            "suspect_mismatch": False,
            "scene_state": None,
            "resolved": False,
        },
        "decision": "keep",
        "version": "v1",
        "stage_trace": [],
    }


def inject_issues(records):
    """在末尾注入构造的脏数据 / 假 PII / 重复。"""
    rng = random.Random(SEED + 1)
    out = list(records)
    start = len(out)
    # 1) 30 条含假 PII（演示脱敏）
    for k in range(30):
        name = rng.choice(FAKE_NAMES)
        phone = rng.choice(FAKE_PHONES)
        addr = rng.choice(FAKE_ADDR)
        cat = rng.choice(list(CATEGORIES.keys()))
        raw = (f"问：我想咨询一下{cat}业务办理。\n"
               f"答：您好{name}先生/女士，您可携带身份证与银行卡到窗口办理，"
               f"如需邮寄请留电话{phone}，收件地址{addr}，我们将在3个工作日内联系您。")
        out.append((cat, raw, {"pii_injected": True}))
    # 2) 20 条格式噪声（演示清洗）：全半角标点混合 + 乱码 + 多余空白
    noises = [
        "问：社保　缴费　记录　怎么　查？？？\n答：请登录人社APP查询。\ufffd\ufffd部分字符损坏",
        "问：公积金贷款额度??如何计算(详见说明)\n答：与账户余额相关,具体以城市公式为准.",
        "问：  营业执照   怎么  线上 办 ？？  \n答：登录政务服务网企业开办专区填报。",
        "问：户口迁移\n怎么办理\n答：凭合法稳定住所证明申请。\ufffd损坏",
    ]
    for k in range(20):
        raw = noises[k % len(noises)]
        out.append((rng.choice(list(CATEGORIES.keys())), raw, {"noise_injected": True}))
    # 3) 10 条精确重复（演示去重）：复制前面已存在的 raw_text
    for k in range(10):
        src = out[rng.randrange(0, len(records))][1]
        out.append(("社保", src, {"dup_injected": True}))
    return out


def main():
    rng = random.Random(SEED)
    base = make_base_records()
    combined = inject_issues(base)
    # 重新编号，保证 sample_id 唯一且连续
    out = []
    for idx, item in enumerate(combined, start=1):
        cat, raw_text = item[0], item[1]
        rec = build_record(idx, cat, raw_text)
        out.append(rec)
    path = "gov_synthetic_300.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"已写出 {len(out)} 条 -> {path}")
    # 统计
    n_pii = sum(1 for it in combined if len(it) > 2 and it[2].get("pii_injected"))
    n_noise = sum(1 for it in combined if len(it) > 2 and it[2].get("noise_injected"))
    n_dup = sum(1 for it in combined if len(it) > 2 and it[2].get("dup_injected"))
    print(f"其中：含假PII {n_pii} 条，格式噪声 {n_noise} 条，精确重复 {n_dup} 条")


if __name__ == "__main__":
    main()
