import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_login_access_token():
    """
    TDD Red Phase: 测试登录接口获取 Token
    预期：
    1. 发送 Email/Password (JSON)
    2. 成功返回 200 和 access_token
    3. 失败返回 401
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Case 1: 尚未实现接口，应该 404 或 405，或者如果实现了但逻辑不对则报错
        # 这里我们预期是 "成功登录" 的逻辑，但因为没写代码，所以肯定失败
        login_data = {
            "email": "test@example.com",
            "password": "testpassword"
        }
        response = await ac.post("/api/auth/login", json=login_data)
        
        # 断言：在 Red 阶段，我们期望这里失败（或者因为 404 失败）
        # 但为了 TDD，我们写出"正确的断言"
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.json()["token_type"] == "bearer"
