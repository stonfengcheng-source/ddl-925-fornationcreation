/**
 * 运行时环境检测模块
 * 用于检测当前运行环境（Web/桌面/Mock）
 */

/// <reference types="vite/client" />

/**
 * 运行环境类型
 */
export type RuntimeMode = 'web' | 'desktop' | 'mock';

/**
 * 检测是否在Tauri环境
 * 通过检查 window 对象上是否存在 __TAURI__ 属性
 */
export const isTauri = (): boolean => {
  return typeof window !== 'undefined' && '__TAURI__' in window;
};

/**
 * 获取当前运行模式
 * 优先级：URL参数 > Tauri检测 > 环境变量
 */
export const getRuntimeMode = (): RuntimeMode => {
  // URL参数强制指定（调试用）
  const urlParams = new URLSearchParams(window.location.search);
  const forceMode = urlParams.get('mode') as RuntimeMode;
  if (forceMode && ['web', 'desktop', 'mock'].includes(forceMode)) {
    return forceMode;
  }

  // 自动检测
  if (isTauri()) return 'desktop';
  if (import.meta.env.VITE_USE_MOCK === 'true') return 'mock';

  return 'web';
};

/**
 * 获取对应模式的API基础URL
 */
export const getBaseURL = (mode?: RuntimeMode): string => {
  const currentMode = mode || getRuntimeMode();

  switch (currentMode) {
    case 'desktop':
      return 'http://localhost:8765/api';
    case 'mock':
      return '/api'; // Mock服务拦截
    case 'web':
    default:
      return '/api'; // Vite代理到远程后端
  }
};

/**
 * 检查是否为开发环境
 */
export const isDev = (): boolean => import.meta.env.DEV;

/**
 * 检查是否为生产环境
 */
export const isProd = (): boolean => import.meta.env.PROD;
