"""节点管理API路由"""
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.models.node import Node
from app.models.user import User
from app.schemas.node import NodeCreate, NodeResponse, NodeHeartbeat, NodeUpdate
from app.schemas.common import SuccessResponse
from app.core.exceptions import ResourceNotFound
from app.api.auth import get_current_user

router = APIRouter()


@router.post("", response_model=SuccessResponse[NodeResponse], status_code=status.HTTP_201_CREATED, summary="注册节点")
async def register_node(node: NodeCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_node = Node(
        node_name=node.node_name,
        node_type=node.node_type,
        ip_address=node.ip_address,
        port=node.port,
        province=node.province,
        city=node.city,
        location=node.location or f"{node.province or ''}{node.city or ''}",
        cpu_cores=node.cpu_cores,
        memory_total=node.memory_total,
        gpu_info=node.gpu_info,
        protocol=node.protocol,
        ssl_enabled=node.ssl_enabled,
        owner_id=current_user.id,
        status="offline",
    )
    db.add(db_node)
    db.commit()
    db.refresh(db_node)
    return SuccessResponse(data=NodeResponse.model_validate(db_node))


@router.get("", response_model=SuccessResponse[List[NodeResponse]], summary="获取节点列表")
async def list_nodes(
    status_filter: Optional[str] = Query(None, alias="status"),
    node_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Node)
    if status_filter:
        query = query.filter(Node.status == status_filter)
    if node_type:
        query = query.filter(Node.node_type == node_type)
    if search:
        query = query.filter(Node.node_name.contains(search))
    nodes = query.order_by(Node.created_at.desc()).all()
    return SuccessResponse(data=[NodeResponse.model_validate(n) for n in nodes])


@router.get("/my", response_model=SuccessResponse[List[NodeResponse]], summary="我的节点")
async def my_nodes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    nodes = db.query(Node).filter(Node.owner_id == current_user.id).order_by(Node.created_at.desc()).all()
    return SuccessResponse(data=[NodeResponse.model_validate(n) for n in nodes])


@router.get("/{node_id}", response_model=SuccessResponse[NodeResponse], summary="获取节点详情")
async def get_node(node_id: str, db: Session = Depends(get_db)):
    db_node = db.query(Node).filter(Node.id == node_id).first()
    if not db_node:
        raise ResourceNotFound(resource="节点")
    return SuccessResponse(data=NodeResponse.model_validate(db_node))


@router.put("/{node_id}", response_model=SuccessResponse[NodeResponse], summary="更新节点")
async def update_node(node_id: str, node_update: NodeUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_node = db.query(Node).filter(Node.id == node_id).first()
    if not db_node:
        raise ResourceNotFound(resource="节点")
    for key, value in node_update.model_dump(exclude_unset=True).items():
        setattr(db_node, key, value)
    db.commit()
    db.refresh(db_node)
    return SuccessResponse(data=NodeResponse.model_validate(db_node))


@router.post("/{node_id}/heartbeat", summary="节点心跳上报")
async def node_heartbeat(node_id: str, heartbeat: NodeHeartbeat, db: Session = Depends(get_db)):
    db_node = db.query(Node).filter(Node.id == node_id).first()
    if not db_node:
        raise ResourceNotFound(resource="节点")
    db_node.cpu_usage = heartbeat.cpu_usage
    db_node.memory_usage = heartbeat.memory_usage
    db_node.disk_usage = heartbeat.disk_usage
    db_node.network_bandwidth = heartbeat.network_bandwidth
    db_node.status = heartbeat.status
    db_node.last_heartbeat = datetime.utcnow()
    db.commit()
    return SuccessResponse(data={"message": "心跳更新成功"})


@router.delete("/{node_id}", summary="删除节点")
async def delete_node(node_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_node = db.query(Node).filter(Node.id == node_id).first()
    if not db_node:
        raise ResourceNotFound(resource="节点")
    db.delete(db_node)
    db.commit()
    return SuccessResponse(data={"message": "删除成功"})
