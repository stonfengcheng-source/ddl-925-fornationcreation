"""数据集管理API路由"""
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.dataset import Dataset
from app.models.user import User
from app.schemas.dataset import DatasetCreate, DatasetResponse, DatasetUpdate
from app.schemas.common import SuccessResponse
from app.core.exceptions import ResourceNotFound
from app.api.auth import get_current_user
from app.services.embedding_hooks import schedule_dataset_embedding

router = APIRouter()


@router.post("", response_model=SuccessResponse[DatasetResponse], status_code=status.HTTP_201_CREATED, summary="创建数据集")
async def create_dataset(dataset: DatasetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_dataset = Dataset(
        name=dataset.name,
        description=dataset.description,
        data_type=dataset.data_type,
        size_bytes=dataset.size_bytes,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        tags=dataset.tags or [],
        quality_score=dataset.quality_score,
        node_id=dataset.node_id,
        columns_info=dataset.columns_info,
        owner_id=current_user.id,
        status="ready",
    )
    db.add(db_dataset)
    db.commit()
    db.refresh(db_dataset)
    # 异步生成 embedding 用于语义匹配
    schedule_dataset_embedding(db_dataset.id)
    return SuccessResponse(data=DatasetResponse.model_validate(db_dataset))


@router.get("", response_model=SuccessResponse[List[DatasetResponse]], summary="获取数据集列表")
async def list_datasets(
    data_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Dataset)
    if data_type:
        query = query.filter(Dataset.data_type == data_type)
    if search:
        query = query.filter(Dataset.name.contains(search))
    datasets = query.order_by(Dataset.created_at.desc()).all()
    return SuccessResponse(data=[DatasetResponse.model_validate(d) for d in datasets])


@router.get("/my", response_model=SuccessResponse[List[DatasetResponse]], summary="我的数据集")
async def my_datasets(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    datasets = db.query(Dataset).filter(Dataset.owner_id == current_user.id).order_by(Dataset.created_at.desc()).all()
    return SuccessResponse(data=[DatasetResponse.model_validate(d) for d in datasets])


@router.get("/{dataset_id}", response_model=SuccessResponse[DatasetResponse], summary="获取数据集详情")
async def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    db_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not db_dataset:
        raise ResourceNotFound(resource="数据集")
    return SuccessResponse(data=DatasetResponse.model_validate(db_dataset))


@router.put("/{dataset_id}", response_model=SuccessResponse[DatasetResponse], summary="更新数据集")
async def update_dataset(dataset_id: str, update: DatasetUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not db_dataset:
        raise ResourceNotFound(resource="数据集")
    for key, value in update.model_dump(exclude_unset=True).items():
        setattr(db_dataset, key, value)
    db.commit()
    db.refresh(db_dataset)
    return SuccessResponse(data=DatasetResponse.model_validate(db_dataset))


@router.delete("/{dataset_id}", summary="删除数据集")
async def delete_dataset(dataset_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not db_dataset:
        raise ResourceNotFound(resource="数据集")
    db.delete(db_dataset)
    db.commit()
    return SuccessResponse(data={"message": "删除成功"})
