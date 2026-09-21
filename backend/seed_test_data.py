"""
种子脚本：预填充乳腺癌联邦学习测试数据
- 1 个 buyer 用户 → 发布乳腺癌分类 FL 任务
- 2 个 provider 用户 → 各自注册数据集 + 节点
运行: python seed_test_data.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.database import SessionLocal, engine, Base, init_db_extensions, ensure_schema_up_to_date
from app.models.user import User
from app.models.task import Task
from app.models.dataset import Dataset
from app.models.node import Node
import uuid

# 确保所有模型已注册
import app.models  # noqa: F401

# 初始化扩展并创建表，补齐缺失列
init_db_extensions()
Base.metadata.create_all(bind=engine)
ensure_schema_up_to_date()
db = SessionLocal()

def get_or_create_user(username, email, user_type):
    u = db.query(User).filter(User.username == username).first()
    if u:
        print(f"  用户已存在: {username} ({u.id})")
        return u
    u = User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        password=None,
        user_type=user_type,
        status="active",
    )
    db.add(u)
    db.flush()
    print(f"  创建用户: {username} (type={user_type}, id={u.id})")
    return u

print("=" * 60)
print("  种子数据：乳腺癌联邦学习测试场景")
print("=" * 60)

# ── 0. Admin ──────────────────────────────────────────
print("\n[0] 创建 admin 用户...")
admin = get_or_create_user("admin", "admin@test.com", "admin")

# ── 1. Buyer: 发布任务 ─────────────────────────────────
print("\n[1] 创建 buyer 用户...")
buyer = get_or_create_user("buyer", "buyer@test.com", "buyer")

# 检查是否已有任务
existing_task = db.query(Task).filter(Task.publisher_id == buyer.id).first()
if existing_task:
    task = existing_task
    print(f"  任务已存在: {task.task_name} ({task.id})")
else:
    task = Task(
        id=str(uuid.uuid4()),
        task_name="乳腺癌良恶性分类联邦学习",
        task_category="医学影像",
        task_description="基于 Wisconsin 乳腺癌数据集，使用联邦学习训练分类模型，在不共享原始数据的前提下实现多中心协作建模。数据包含 30 个细胞核测量特征，目标为良性/恶性二分类。",
        task_tags=["乳腺癌", "联邦学习", "二分类", "医学", "sklearn"],
        status="pending",
        min_data_size=100,
        min_nodes=2,
        max_nodes=5,
        data_formats=["tabular", "csv"],
        privacy_level="medium",
        model_type="breast_cancer",
        aggregation_strategy="fedavg",
        target_accuracy=0.90,
        max_rounds=5,
        reward_pool=30000,
        reward_currency="CNY",
        publisher_id=buyer.id,
    )
    db.add(task)
    db.flush()
    print(f"  创建任务: {task.task_name} ({task.id})")

# ── 2. Provider A ──────────────────────────────────────
print("\n[2] 创建 provider_a 用户 + 数据集 + 节点...")
provider_a = get_or_create_user("provider_a", "provider_a@test.com", "provider")

if not db.query(Dataset).filter(Dataset.owner_id == provider_a.id).first():
    ds_a = Dataset(
        id=str(uuid.uuid4()),
        name="乳腺癌细胞核测量数据 - 医院A",
        description="Wisconsin 乳腺癌数据集 A 分区：包含 284 例样本，30 个细胞核特征（半径、纹理、周长、面积、光滑度等）",
        data_type="tabular",
        row_count=284,
        column_count=30,
        tags=["乳腺癌", "细胞核", "tabular", "医学", "sklearn"],
        quality_score=0.92,
        status="ready",
        owner_id=provider_a.id,
        columns_info=[
            {"name": "mean_radius", "type": "numeric"},
            {"name": "mean_texture", "type": "numeric"},
            {"name": "mean_perimeter", "type": "numeric"},
            {"name": "mean_area", "type": "numeric"},
            {"name": "mean_smoothness", "type": "numeric"},
            {"name": "mean_compactness", "type": "numeric"},
            {"name": "mean_concavity", "type": "numeric"},
            {"name": "mean_concave_points", "type": "numeric"},
            {"name": "mean_symmetry", "type": "numeric"},
            {"name": "mean_fractal_dimension", "type": "numeric"},
        ],
    )
    db.add(ds_a)
    print(f"  创建数据集: {ds_a.name}")
else:
    print("  数据集已存在 (provider_a)")

if not db.query(Node).filter(Node.owner_id == provider_a.id).first():
    node_a = Node(
        id=str(uuid.uuid4()),
        node_name="医院A-训练节点",
        node_type="training",
        status="online",
        ip_address="192.168.1.101",
        port=8081,
        cpu_cores=8,
        memory_total="32GB",
        gpu_info="NVIDIA RTX 3060",
        owner_id=provider_a.id,
    )
    db.add(node_a)
    print(f"  创建节点: {node_a.node_name}")
else:
    print("  节点已存在 (provider_a)")

# ── 3. Provider B ──────────────────────────────────────
print("\n[3] 创建 provider_b 用户 + 数据集 + 节点...")
provider_b = get_or_create_user("provider_b", "provider_b@test.com", "provider")

if not db.query(Dataset).filter(Dataset.owner_id == provider_b.id).first():
    ds_b = Dataset(
        id=str(uuid.uuid4()),
        name="乳腺癌细胞核测量数据 - 医院B",
        description="Wisconsin 乳腺癌数据集 B 分区：包含 285 例样本，30 个细胞核特征（半径、纹理、周长、面积、光滑度等）",
        data_type="tabular",
        row_count=285,
        column_count=30,
        tags=["乳腺癌", "细胞核", "tabular", "医学", "sklearn"],
        quality_score=0.89,
        status="ready",
        owner_id=provider_b.id,
        columns_info=[
            {"name": "mean_radius", "type": "numeric"},
            {"name": "mean_texture", "type": "numeric"},
            {"name": "mean_perimeter", "type": "numeric"},
            {"name": "mean_area", "type": "numeric"},
            {"name": "mean_smoothness", "type": "numeric"},
            {"name": "mean_compactness", "type": "numeric"},
            {"name": "mean_concavity", "type": "numeric"},
            {"name": "mean_concave_points", "type": "numeric"},
            {"name": "mean_symmetry", "type": "numeric"},
            {"name": "mean_fractal_dimension", "type": "numeric"},
        ],
    )
    db.add(ds_b)
    print(f"  创建数据集: {ds_b.name}")
else:
    print("  数据集已存在 (provider_b)")

if not db.query(Node).filter(Node.owner_id == provider_b.id).first():
    node_b = Node(
        id=str(uuid.uuid4()),
        node_name="医院B-训练节点",
        node_type="training",
        status="online",
        ip_address="192.168.1.102",
        port=8082,
        cpu_cores=4,
        memory_total="16GB",
        gpu_info="NVIDIA RTX 2060",
        owner_id=provider_b.id,
    )
    db.add(node_b)
    print(f"  创建节点: {node_b.node_name}")
else:
    print("  节点已存在 (provider_b)")

db.commit()
db.close()

print("\n" + "=" * 60)
print("  种子数据创建完成！")
print("  本地免密登录账号: admin / buyer / provider_a / provider_b")
print("=" * 60)
