import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { useUserStore, UserRole } from '@/store/useUserStore';
import { Permission, hasPermission, hasRole } from '@/config/permissions';

interface AuthGuardProps {
  children: React.ReactNode;
  /** 要求的角色（单个角色或角色数组） */
  requiredRole?: UserRole | UserRole[];
  /** 要求的权限（单个权限或权限数组，满足其一即可） */
  requiredPermission?: Permission | Permission[];
}

/**
 * 认证路由守卫组件
 * - 检查用户是否已登录
 * - 检查用户是否有权限访问（支持角色检查和权限检查）
 */
const AuthGuard: React.FC<AuthGuardProps> = ({
  children,
  requiredRole,
  requiredPermission,
}) => {
  const { isAuthenticated, user } = useUserStore();
  const location = useLocation();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    // 模拟短暂的检查时间，确保状态已从 localStorage 恢复
    const timer = setTimeout(() => {
      setIsChecking(false);
    }, 100);

    return () => clearTimeout(timer);
  }, []);

  // 检查状态中，显示加载
  if (isChecking) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Spin size="large" tip="加载中..." />
      </div>
    );
  }

  // 未登录，重定向到登录页
  if (!isAuthenticated) {
    return <Navigate to="/" state={{ from: location }} replace />;
  }

  const userRole = user?.role ?? null;

  // 检查角色权限（支持单个角色或角色数组）
  if (requiredRole && userRole) {
    const requiredRoles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
    if (!hasRole(userRole, requiredRoles)) {
      return <Navigate to="/403" replace />;
    }
  }

  // 检查功能权限（支持单个权限或权限数组，满足其一即可）
  if (requiredPermission && userRole) {
    const requiredPermissions = Array.isArray(requiredPermission)
      ? requiredPermission
      : [requiredPermission];
    const hasAnyPermission = requiredPermissions.some((permission) =>
      hasPermission(userRole, permission)
    );
    if (!hasAnyPermission) {
      return <Navigate to="/403" replace />;
    }
  }

  // 通过检查，渲染子组件
  return <>{children}</>;
};

export default AuthGuard;
