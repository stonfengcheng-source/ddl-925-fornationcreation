import axios from 'axios';
import type { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { message } from 'antd';
import { useUserStore } from '@/store/useUserStore';
import { getBaseURL, getRuntimeMode } from '@/utils/env';

/**
 * 创建 axios 实例（根据环境动态设置baseURL）
 */
const request = axios.create({
  baseURL: getBaseURL(),
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 动态切换API基础URL
 * 用于桌面环境检测本地服务不可用时的降级
 */
export const setBaseURL = (url: string): void => {
  request.defaults.baseURL = url;
};

/**
 * 恢复环境默认的baseURL
 */
export const resetBaseURL = (): void => {
  request.defaults.baseURL = getBaseURL();
};

/**
 * 请求拦截器
 * - 自动添加 Authorization Header
 */
request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useUserStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

/**
 * 响应拦截器
 * - 统一错误处理
 * - Token 过期处理
 * - 桌面模式本地服务不可用特殊处理
 */
request.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error: AxiosError) => {
    // 桌面模式下本地服务不可用的特殊提示
    if (getRuntimeMode() === 'desktop' && !error.response) {
      message.error('本地服务未启动，请检查节点状态');
      return Promise.reject(error);
    }

    if (error.response) {
      const { status, data } = error.response as any;

      const msg = data?.detail || data?.error?.message || data?.message;

      switch (status) {
        case 400:
          message.error(msg || '请求参数错误');
          break;
        case 401: {
          // 登录接口的401不应触发跳转，由登录页面自行处理错误提示
          const url = (error.config as any)?.url || '';
          if (url.includes('/auth/login')) {
            // 不做任何全局提示，让调用方 catch 处理
          } else {
            message.error('登录已过期，请重新登录');
            useUserStore.getState().logout();
            window.location.href = '/';
          }
          break;
        }
        case 403: {
          const url403 = (error.config as any)?.url || '';
          if (url403.includes('/auth/login')) {
            // 角色登录限制，由调用方 catch 处理
          } else {
            message.error(msg || '无权限访问该资源');
          }
          break;
        }
        case 404:
          message.error(msg || '请求的资源不存在');
          break;
        case 500:
          message.error(msg || '服务器内部错误，请稍后重试');
          break;
        default:
          message.error(msg || '请求失败，请稍后重试');
      }
    } else if (error.request) {
      message.error('网络错误，请检查网络连接');
    } else {
      message.error('请求配置错误');
    }

    return Promise.reject(error);
  }
);

export default request;
