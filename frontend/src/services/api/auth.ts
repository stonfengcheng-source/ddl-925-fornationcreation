import request from '@/services/request';
import { User } from '@/store/useUserStore';

/**
 * 登录请求参数
 */
export interface LoginParams {
  username: string;
  password: string;
}

/**
 * 登录响应
 */
export interface LoginResponse {
  user: User;
  token: string;
}

/**
 * 注册请求参数
 */
export interface RegisterParams {
  username: string;
  email: string;
  password: string;
  userType: 'buyer' | 'provider' | 'admin';
}

/**
 * 重置密码请求参数
 */
export interface ResetPasswordParams {
  email: string;
  code: string;
  newPassword: string;
}

/**
 * 认证相关 API
 */
export const authApi = {
  /**
   * 用户登录
   * @param params - 登录参数
   */
  login: (params: LoginParams) =>
    request.post<LoginResponse>('/auth/login', params),

  /**
   * 用户注册
   * @param params - 注册参数
   */
  register: (params: RegisterParams) =>
    request.post<{ message: string }>('/auth/register', {
      username: params.username,
      email: params.email,
      password: params.password,
      user_type: params.userType,
    }),

  /**
   * 发送重置密码验证码
   * @param email - 用户邮箱
   */
  sendResetCode: (email: string) =>
    request.post<{ message: string }>('/auth/send-reset-code', { email }),

  /**
   * 重置密码
   * @param params - 重置密码参数
   */
  resetPassword: (params: ResetPasswordParams) =>
    request.post<{ message: string }>('/auth/reset-password', params),

  /**
   * 刷新 Token
   */
  refreshToken: () =>
    request.post<{ token: string }>('/auth/refresh'),

  /**
   * 获取当前用户信息
   */
  getCurrentUser: () =>
    request.get<User>('/auth/me'),
};

export default authApi;
