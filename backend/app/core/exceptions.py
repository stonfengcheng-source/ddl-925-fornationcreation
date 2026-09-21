"""
自定义异常类
"""
from fastapi import HTTPException, status
from typing import Optional, List, Dict, Any

class APIException(HTTPException):
    """自定义 API 异常基类"""
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[List[Dict[str, str]]] = None
    ):
        self.error_code = error_code
        self.details = details
        super().__init__(
            status_code=status_code,
            detail={
                "error": {
                    "code": error_code,
                    "message": message,
                    "details": details or []
                }
            }
        )

class ValidationError(APIException):
    """参数验证错误 (400)"""
    def __init__(self, message: str = "请求参数验证失败", details: Optional[List[Dict[str, str]]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            message=message,
            details=details
        )

class ResourceNotFound(APIException):
    """资源不存在 (404)"""
    def __init__(self, resource: str = "资源"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            message=f"{resource}不存在"
        )

class DuplicateResource(APIException):
    """资源已存在 (409)"""
    def __init__(self, message: str = "资源已存在"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            error_code="DUPLICATE_RESOURCE",
            message=message
        )

class BusinessLogicError(APIException):
    """业务逻辑错误 (422)"""
    def __init__(self, error_code: str, message: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code=error_code,
            message=message
        )
