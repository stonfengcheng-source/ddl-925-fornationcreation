/**
 * 权限检查 Hook
 * 提供便捷的权限检查功能
 */

import { useMemo } from 'react';
import { useUserStore, UserRole } from '@/store/useUserStore';
import {
  Permission,
  hasPermission,
  hasAnyPermission,
  hasAllPermissions,
  hasRole,
  getRoleDisplayName,
} from '@/config/permissions';

export interface UsePermissionReturn {
  /** 当前用户角色 */
  role: UserRole | null;
  /** 是否已认证 */
  isAuthenticated: boolean;
  /** 是否是管理员 */
  isAdmin: boolean;
  /** 是否是需求方 */
  isBuyer: boolean;
  /** 是否是数据提供方 */
  isProvider: boolean;
  /** 角色显示名称 */
  roleDisplayName: string;
  /** 检查是否有指定权限 */
  hasPermission: (permission: Permission) => boolean;
  /** 检查是否有任意一个指定权限 */
  hasAnyPermission: (permissions: Permission[]) => boolean;
  /** 检查是否有所有指定权限 */
  hasAllPermissions: (permissions: Permission[]) => boolean;
  /** 检查是否匹配指定角色 */
  hasRole: (roles: UserRole[]) => boolean;
  /** 检查菜单项是否可见 */
  isMenuVisible: (menuPath: string) => boolean;
}

/**
 * 权限检查 Hook
 * @returns UsePermissionReturn
 */
export function usePermission(): UsePermissionReturn {
  const { user, isAuthenticated } = useUserStore();
  const role = user?.role ?? null;

  return useMemo(() => {
    return {
      role,
      isAuthenticated,
      isAdmin: role === 'admin',
      isBuyer: role === 'buyer',
      isProvider: role === 'provider',
      roleDisplayName: getRoleDisplayName(role),
      hasPermission: (permission: Permission) => hasPermission(role, permission),
      hasAnyPermission: (permissions: Permission[]) => hasAnyPermission(role, permissions),
      hasAllPermissions: (permissions: Permission[]) => hasAllPermissions(role, permissions),
      hasRole: (roles: UserRole[]) => hasRole(role, roles),
      isMenuVisible: (menuPath: string) => {
        // 导入 MENU_VISIBILITY 进行匹配
        const { MENU_VISIBILITY } = require('@/config/permissions');
        const allowedRoles = MENU_VISIBILITY[menuPath];
        if (!allowedRoles) return true; // 未配置的菜单默认可见
        return allowedRoles.includes(role);
      },
    };
  }, [role, isAuthenticated]);
}

export default usePermission;
