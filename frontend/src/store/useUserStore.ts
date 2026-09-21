import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * 用户角色类型
 */
export type UserRole = 'buyer' | 'provider' | 'admin';

/**
 * 用户信息接口
 */
export interface User {
  userId: string;
  username: string;
  email: string;
  role: UserRole;
  avatar?: string;
}

/**
 * 认证状态接口
 */
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;

  // Actions
  login: (user: User, token: string) => void;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
  updateToken: (token: string) => void;
}

/**
 * 认证状态管理 Store
 * 使用 Zustand + persist 中间件实现持久化
 */
export const useUserStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      /**
       * 登录
       * @param user - 用户信息
       * @param token - JWT Token
       */
      login: (user, token) =>
        set({
          user,
          token,
          isAuthenticated: true,
        }),

      /**
       * 登出
       * 清除所有认证信息
       */
      logout: () =>
        set({
          user: null,
          token: null,
          isAuthenticated: false,
        }),

      /**
       * 更新用户信息
       * @param user - 部分用户信息
       */
      updateUser: (user) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...user } : null,
        })),

      /**
       * 更新 Token
       * @param token - 新的 JWT Token
       */
      updateToken: (token) =>
        set({
          token,
        }),

    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

export default useUserStore;
