/**
 * 运行时环境检测Hook
 */

import { useState, useEffect, useCallback } from 'react';
import { getRuntimeMode, isTauri, type RuntimeMode } from '@/utils/env';
import { localNodeApi } from '@/services/api/localNode';

interface UseRuntimeReturn {
  /** 当前运行模式 */
  mode: RuntimeMode;
  /** 是否在Tauri环境 */
  isDesktop: boolean;
  /** 本地服务是否可用（仅桌面模式） */
  isLocalServiceReady: boolean;
  /** 检查本地服务状态 */
  checkLocalService: () => Promise<boolean>;
}

/**
 * 运行时环境检测Hook
 */
export const useRuntime = (): UseRuntimeReturn => {
  const [mode] = useState<RuntimeMode>(getRuntimeMode());
  const [isLocalServiceReady, setIsLocalServiceReady] = useState(false);

  const checkLocalService = useCallback(async (): Promise<boolean> => {
    if (mode !== 'desktop') {
      setIsLocalServiceReady(false);
      return false;
    }
    const status = await localNodeApi.checkHealth();
    setIsLocalServiceReady(status);
    return status;
  }, [mode]);

  // 桌面模式下定期检查本地服务
  useEffect(() => {
    if (mode === 'desktop') {
      checkLocalService();
      const interval = setInterval(checkLocalService, 10000);
      return () => clearInterval(interval);
    }
  }, [mode, checkLocalService]);

  return {
    mode,
    isDesktop: isTauri(),
    isLocalServiceReady,
    checkLocalService,
  };
};

export default useRuntime;
