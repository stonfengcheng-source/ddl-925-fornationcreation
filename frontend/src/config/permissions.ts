/**
 * 权限配置文件
 * 定义所有权限点和角色权限映射
 */

import { UserRole } from '@/store/useUserStore';

/**
 * 权限点定义
 */
export type Permission =
  | 'task:publish' // 发布任务 - buyer, admin
  | 'task:join' // 参与任务 - provider, admin
  | 'task:view' // 查看任务 - all roles
  | 'dataasset:create' // 创建数据资产 - provider, admin
  | 'dataasset:view' // 查看数据资产 - provider, admin
  | 'dataasset:manage' // 管理数据资产 - provider, admin
  | 'node:register' // 注册节点 - provider, admin
  | 'node:manage' // 管理节点 - provider(owner), admin
  | 'node:view' // 查看节点 - all roles
  | 'qualityrule:manage' // 管理质量规则 - provider, admin
  | 'privacybudget:view' // 查看隐私预算 - all roles
  | 'admin:access'; // 访问管理后台 - admin only

/**
 * 角色权限映射
 * 定义每个角色拥有的权限
 */
export const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  buyer: [
    'task:publish',
    'task:view',
    'node:view',
    'privacybudget:view',
  ],
  provider: [
    'task:join',
    'task:view',
    'dataasset:create',
    'dataasset:view',
    'dataasset:manage',
    'node:register',
    'node:manage',
    'node:view',
    'qualityrule:manage',
    'privacybudget:view',
  ],
  admin: [
    'task:publish',
    'task:join',
    'task:view',
    'dataasset:create',
    'dataasset:view',
    'dataasset:manage',
    'node:register',
    'node:manage',
    'node:view',
    'qualityrule:manage',
    'privacybudget:view',
    'admin:access',
  ],
};

/**
 * 菜单项可见角色配置
 * 用于 Layout 导航菜单过滤
 */
export const MENU_VISIBILITY: Record<string, UserRole[]> = {
  '/dashboard': ['buyer', 'admin'],
  '/tasks': ['buyer', 'admin'],
  '/tasks/publish': ['buyer', 'admin'],
  '/my-tasks': ['buyer', 'admin'],
  '/data-assets': ['admin'],
  '/matching': ['admin'],
  '/quality-rules': ['admin'],
  '/privacy-budget': ['buyer', 'admin'],
  '/edge-nodes': ['admin'],
  '/edge-nodes/register': ['admin'],
  '/profile': ['buyer', 'admin'],
  '/profile/wallet': ['buyer', 'admin'],
  '/notifications': ['buyer', 'admin'],
  '/admin': ['admin'],
};

/**
 * 检查角色是否拥有指定权限
 * @param role - 用户角色
 * @param permission - 权限点
 * @returns boolean
 */
export function hasPermission(role: UserRole | null | undefined, permission: Permission): boolean {
  if (!role) return false;
  return ROLE_PERMISSIONS[role].includes(permission);
}

/**
 * 检查角色是否拥有任意一个指定权限
 * @param role - 用户角色
 * @param permissions - 权限点数组
 * @returns boolean
 */
export function hasAnyPermission(role: UserRole | null | undefined, permissions: Permission[]): boolean {
  if (!role) return false;
  return permissions.some((permission) => ROLE_PERMISSIONS[role].includes(permission));
}

/**
 * 检查角色是否拥有所有指定权限
 * @param role - 用户角色
 * @param permissions - 权限点数组
 * @returns boolean
 */
export function hasAllPermissions(role: UserRole | null | undefined, permissions: Permission[]): boolean {
  if (!role) return false;
  return permissions.every((permission) => ROLE_PERMISSIONS[role].includes(permission));
}

/**
 * 检查角色是否匹配要求
 * @param role - 用户角色
 * @param requiredRoles - 要求的角色数组
 * @returns boolean
 */
export function hasRole(role: UserRole | null | undefined, requiredRoles: UserRole[]): boolean {
  if (!role) return false;
  return requiredRoles.includes(role);
}

/**
 * 获取角色的显示名称
 * @param role - 用户角色
 * @returns 显示名称
 */
export function getRoleDisplayName(role: UserRole | null | undefined): string {
  const displayNames: Record<UserRole, string> = {
    buyer: '需求方',
    provider: '数据提供方',
    admin: '管理员',
  };
  return role ? displayNames[role] : '未知';
}
