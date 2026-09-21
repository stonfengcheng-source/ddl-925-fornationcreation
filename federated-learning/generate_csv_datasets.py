"""
生成所有6个CSV样本数据集
- breast_cancer: sklearn内置乳腺癌数据集
- diabetes: sklearn内置糖尿病数据集
- heart_disease: UCI Cleveland心脏病数据集 (通过sklearn fetch_openml)
- credit_score: UCI German Credit数据集 (通过sklearn fetch_openml)
- adult_income: UCI Adult Census收入数据集 (通过sklearn fetch_openml)
- bank_marketing: UCI Bank Marketing数据集 (通过sklearn fetch_openml)
"""

import os
import numpy as np
import pandas as pd
from sklearn.datasets import load_breast_cancer, load_diabetes

OUT_DIR = os.path.join(os.path.dirname(__file__), "sample_data")
os.makedirs(OUT_DIR, exist_ok=True)


def gen_breast_cancer():
    """sklearn 内置乳腺癌数据集 -> CSV"""
    data = load_breast_cancer()
    df = pd.DataFrame(data.data, columns=data.feature_names)
    df["target"] = data.target  # 0=恶性, 1=良性
    path = os.path.join(OUT_DIR, "breast_cancer.csv")
    df.to_csv(path, index=False)
    print(f"✓ breast_cancer: {df.shape} -> {path}")


def gen_diabetes():
    """sklearn 内置糖尿病数据集 -> CSV"""
    data = load_diabetes()
    df = pd.DataFrame(data.data, columns=data.feature_names)
    df["target"] = data.target
    path = os.path.join(OUT_DIR, "diabetes.csv")
    df.to_csv(path, index=False)
    print(f"✓ diabetes: {df.shape} -> {path}")


def gen_heart_disease():
    """
    UCI Cleveland Heart Disease 数据集
    https://archive.ics.uci.edu/ml/datasets/heart+disease
    13个特征 + 1个目标(0=无心脏病, 1=有心脏病)
    """
    try:
        from sklearn.datasets import fetch_openml
        heart = fetch_openml(name="heart-statlog", version=1, as_frame=True, parser="auto")
        df = heart.frame.copy()
        # target 列: 1=absent, 2=present -> 转为 0/1
        df["target"] = (df["target"].astype(int) == 2).astype(int)
        # 重命名列为更有意义的名称
        col_names = [
            "age", "sex", "chest_pain_type", "resting_blood_pressure",
            "serum_cholesterol", "fasting_blood_sugar", "resting_ecg",
            "max_heart_rate", "exercise_angina", "oldpeak",
            "slope", "num_major_vessels", "thal", "target"
        ]
        if len(df.columns) == len(col_names):
            df.columns = col_names
    except Exception as e:
        print(f"  fetch_openml failed ({e}), generating from UCI data directly...")
        # Fallback: 使用经典的 Cleveland 数据集特征手动构造
        from sklearn.datasets import fetch_openml
        try:
            heart = fetch_openml(data_id=53, as_frame=True, parser="auto")
            df = heart.frame.copy()
            target_col = df.columns[-1]
            df["target"] = (df[target_col].astype(float) > 0).astype(int)
            if target_col != "target":
                df = df.drop(columns=[target_col])
        except Exception as e2:
            print(f"  Second attempt failed ({e2}), using synthetic heart disease data...")
            np.random.seed(42)
            n = 303
            df = pd.DataFrame({
                "age": np.random.randint(29, 77, n),
                "sex": np.random.randint(0, 2, n),
                "chest_pain_type": np.random.randint(1, 5, n),
                "resting_blood_pressure": np.random.randint(94, 200, n),
                "serum_cholesterol": np.random.randint(126, 564, n),
                "fasting_blood_sugar": np.random.randint(0, 2, n),
                "resting_ecg": np.random.randint(0, 3, n),
                "max_heart_rate": np.random.randint(71, 202, n),
                "exercise_angina": np.random.randint(0, 2, n),
                "oldpeak": np.round(np.random.uniform(0, 6.2, n), 1),
                "slope": np.random.randint(1, 4, n),
                "num_major_vessels": np.random.randint(0, 4, n),
                "thal": np.random.choice([3, 6, 7], n),
                "target": np.random.randint(0, 2, n),
            })

    path = os.path.join(OUT_DIR, "heart_disease.csv")
    df.to_csv(path, index=False)
    print(f"✓ heart_disease: {df.shape} -> {path}")


def gen_credit_score():
    """
    UCI German Credit 数据集
    https://archive.ics.uci.edu/ml/datasets/statlog+(german+credit+data)
    20个特征 + 1个目标(1=good, 2=bad -> 0/1)
    """
    try:
        from sklearn.datasets import fetch_openml
        credit = fetch_openml(name="credit-g", version=1, as_frame=True, parser="auto")
        df = credit.frame.copy()
        # target: good/bad -> 0/1
        df["target"] = (df["class"] == "bad").astype(int)
        df = df.drop(columns=["class"])
        # 将分类列编码为数值
        for col in df.select_dtypes(include=["category", "object"]).columns:
            df[col] = df[col].astype("category").cat.codes
    except Exception as e:
        print(f"  fetch_openml failed ({e}), using fallback...")
        np.random.seed(43)
        n = 1000
        df = pd.DataFrame({
            "checking_status": np.random.randint(0, 4, n),
            "duration": np.random.randint(4, 72, n),
            "credit_history": np.random.randint(0, 5, n),
            "purpose": np.random.randint(0, 11, n),
            "credit_amount": np.random.randint(250, 18425, n),
            "savings_status": np.random.randint(0, 5, n),
            "employment": np.random.randint(0, 5, n),
            "installment_commitment": np.random.randint(1, 5, n),
            "personal_status": np.random.randint(0, 5, n),
            "other_parties": np.random.randint(0, 3, n),
            "residence_since": np.random.randint(1, 5, n),
            "property_magnitude": np.random.randint(0, 4, n),
            "age": np.random.randint(19, 75, n),
            "other_payment_plans": np.random.randint(0, 3, n),
            "housing": np.random.randint(0, 3, n),
            "existing_credits": np.random.randint(1, 5, n),
            "job": np.random.randint(0, 4, n),
            "num_dependents": np.random.randint(1, 3, n),
            "own_telephone": np.random.randint(0, 2, n),
            "foreign_worker": np.random.randint(0, 2, n),
            "target": np.random.randint(0, 2, n),
        })

    path = os.path.join(OUT_DIR, "credit_score.csv")
    df.to_csv(path, index=False)
    print(f"✓ credit_score: {df.shape} -> {path}")


def gen_adult_income():
    """
    UCI Adult/Census Income 数据集
    https://archive.ics.uci.edu/ml/datasets/adult
    14个特征 + 1个目标(<=50K / >50K -> 0/1)
    """
    try:
        from sklearn.datasets import fetch_openml
        adult = fetch_openml(name="adult", version=2, as_frame=True, parser="auto")
        df = adult.frame.copy()
        target_col = "income" if "income" in df.columns else df.columns[-1]
        # target: <=50K -> 0, >50K -> 1
        df["target"] = df[target_col].astype(str).str.strip().str.replace(".", "", regex=False)
        df["target"] = (df["target"].isin([">50K", ">50K."])).astype(int)
        df = df.drop(columns=[target_col])
        # 编码分类列
        for col in df.select_dtypes(include=["category", "object"]).columns:
            if col != "target":
                df[col] = df[col].astype("category").cat.codes
    except Exception as e:
        print(f"  fetch_openml failed ({e}), using fallback...")
        np.random.seed(44)
        n = 5000  # 使用较小子集
        df = pd.DataFrame({
            "age": np.random.randint(17, 90, n),
            "workclass": np.random.randint(0, 8, n),
            "fnlwgt": np.random.randint(12285, 1484705, n),
            "education": np.random.randint(0, 16, n),
            "education_num": np.random.randint(1, 16, n),
            "marital_status": np.random.randint(0, 7, n),
            "occupation": np.random.randint(0, 14, n),
            "relationship": np.random.randint(0, 6, n),
            "race": np.random.randint(0, 5, n),
            "sex": np.random.randint(0, 2, n),
            "capital_gain": np.random.randint(0, 99999, n),
            "capital_loss": np.random.randint(0, 4356, n),
            "hours_per_week": np.random.randint(1, 99, n),
            "native_country": np.random.randint(0, 41, n),
            "target": np.random.randint(0, 2, n),
        })

    path = os.path.join(OUT_DIR, "adult_income.csv")
    df.to_csv(path, index=False)
    print(f"✓ adult_income: {df.shape} -> {path}")


def gen_bank_marketing():
    """
    UCI Bank Marketing 数据集
    https://archive.ics.uci.edu/ml/datasets/bank+marketing
    16个特征 + 1个目标(no/yes -> 0/1)
    """
    try:
        from sklearn.datasets import fetch_openml
        bank = fetch_openml(name="bank-marketing", version=1, as_frame=True, parser="auto")
        df = bank.frame.copy()
        target_col = df.columns[-1]
        # target: 1/2 or no/yes -> 0/1
        if df[target_col].dtype == "category" or df[target_col].dtype == object:
            df["target"] = (df[target_col].astype(str).str.strip().isin(["yes", "2"])).astype(int)
        else:
            df["target"] = (df[target_col].astype(int) == 2).astype(int)
        df = df.drop(columns=[target_col])
        # 编码分类列
        for col in df.select_dtypes(include=["category", "object"]).columns:
            if col != "target":
                df[col] = df[col].astype("category").cat.codes
    except Exception as e:
        print(f"  fetch_openml failed ({e}), using fallback...")
        np.random.seed(45)
        n = 4521
        df = pd.DataFrame({
            "age": np.random.randint(18, 95, n),
            "job": np.random.randint(0, 12, n),
            "marital": np.random.randint(0, 3, n),
            "education": np.random.randint(0, 4, n),
            "default": np.random.randint(0, 2, n),
            "balance": np.random.randint(-8019, 102127, n),
            "housing": np.random.randint(0, 2, n),
            "loan": np.random.randint(0, 2, n),
            "contact": np.random.randint(0, 3, n),
            "day": np.random.randint(1, 31, n),
            "month": np.random.randint(0, 12, n),
            "duration": np.random.randint(0, 4918, n),
            "campaign": np.random.randint(1, 63, n),
            "pdays": np.random.randint(-1, 871, n),
            "previous": np.random.randint(0, 275, n),
            "poutcome": np.random.randint(0, 4, n),
            "target": np.random.randint(0, 2, n),
        })

    path = os.path.join(OUT_DIR, "bank_marketing.csv")
    df.to_csv(path, index=False)
    print(f"✓ bank_marketing: {df.shape} -> {path}")


if __name__ == "__main__":
    print("=" * 50)
    print("生成联邦学习样本CSV数据集")
    print("=" * 50)
    gen_breast_cancer()
    gen_diabetes()
    gen_heart_disease()
    gen_credit_score()
    gen_adult_income()
    gen_bank_marketing()
    print("=" * 50)
    print("全部数据集生成完成！")
