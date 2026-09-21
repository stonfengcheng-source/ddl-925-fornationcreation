/**
 * 本地节点API（仅桌面环境可用）
 * 通过Tauri IPC调用Rust层，或HTTP调用本地Python服务
 */

import { isTauri } from '@/utils/env';
import type {
  DataFileInfo,
  LocalNodeConfig,
  LocalTrainingConfig,
  LocalTrainingStatus,
} from '@/types/env';

// Tauri API 类型声明（避免直接依赖 @tauri-apps/api 包）
declare global {
  interface Window {
    __TAURI__?: {
      invoke: (cmd: string, args?: Record<string, unknown>) => Promise<unknown>;
    };
  }
}

/**
 * Tauri IPC调用封装
 */
const tauriInvoke = async <T>(cmd: string, args?: Record<string, unknown>): Promise<T> => {
  if (!window.__TAURI__) {
    throw new Error('Tauri API 不可用');
  }
  return window.__TAURI__.invoke(cmd, args) as Promise<T>;
};

/**
 * Tauri IPC调用封装（仅桌面环境）
 */
export const localNodeApi = {
  /**
   * 启动本地Python服务
   */
  async startLocalNode(config: {
    nodeId: string;
    nodeName: string;
    aggregatorUrl: string;
  }): Promise<void> {
    if (!isTauri()) {
      throw new Error('此功能仅在桌面客户端可用');
    }

    const dataDir = await this.getDataDirectory();

    await tauriInvoke('start_python_sidecar', {
      config: {
        ...config,
        data_directory: dataDir,
      },
    });
  },

  /**
   * 停止本地Python服务
   */
  async stopLocalNode(): Promise<void> {
    if (!isTauri()) return;
    await tauriInvoke('stop_python_sidecar');
  },

  /**
   * 检查本地服务健康状态
   */
  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch('http://localhost:8765/health', {
        method: 'GET',
        signal: AbortSignal.timeout(3000),
      });
      return response.ok;
    } catch {
      return false;
    }
  },

  /**
   * 选择本地数据文件
   */
  async selectDataFile(): Promise<DataFileInfo | null> {
    if (!isTauri()) {
      throw new Error('此功能仅在桌面客户端可用');
    }
    return tauriInvoke<DataFileInfo | null>('select_data_file');
  },

  /**
   * 导入数据到工作区
   */
  async importData(sourcePath: string, nodeId: string): Promise<string> {
    if (!isTauri()) {
      throw new Error('此功能仅在桌面客户端可用');
    }
    return tauriInvoke<string>('import_data_to_workspace', { sourcePath, nodeId });
  },

  /**
   * 获取本地数据目录
   */
  async getDataDirectory(): Promise<string> {
    if (!isTauri()) return '';
    return tauriInvoke<string>('get_data_directory');
  },

  /**
   * 获取工作区文件列表
   */
  async listWorkspaceFiles(nodeId: string): Promise<DataFileInfo[]> {
    if (!isTauri()) return [];
    return tauriInvoke<DataFileInfo[]>('list_workspace_files', { nodeId });
  },

  /**
   * 清理工作区
   */
  async clearWorkspace(nodeId: string): Promise<void> {
    if (!isTauri()) return;
    await tauriInvoke('clear_workspace', { nodeId });
  },
};

/**
 * 本地训练API（HTTP调用Python服务）
 */
export const localTrainingApi = {
  baseURL: 'http://localhost:8765',

  /**
   * 初始化节点配置
   */
  async initializeNode(config: LocalNodeConfig): Promise<void> {
    const res = await fetch(`${this.baseURL}/api/node/init`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error('初始化失败');
  },

  /**
   * 获取数据文件列表
   */
  async getDataFiles(): Promise<DataFileInfo[]> {
    const res = await fetch(`${this.baseURL}/api/data/files`);
    const data = await res.json();
    return data.files as DataFileInfo[];
  },

  /**
   * 预览数据
   */
  async previewData(
    filePath: string,
    rows: number = 5
  ): Promise<{
    preview: string[][];
    columns: string[];
    total_rows: number;
  }> {
    const res = await fetch(`${this.baseURL}/api/data/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: filePath, rows }),
    });
    return res.json();
  },

  /**
   * 启动训练
   */
  async startTraining(config: LocalTrainingConfig): Promise<void> {
    const res = await fetch(`${this.baseURL}/api/training/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error('启动训练失败');
  },

  /**
   * 停止训练
   */
  async stopTraining(): Promise<void> {
    await fetch(`${this.baseURL}/api/training/stop`, { method: 'POST' });
  },

  /**
   * 获取训练状态
   */
  async getTrainingStatus(): Promise<LocalTrainingStatus> {
    const res = await fetch(`${this.baseURL}/api/training/status`);
    return res.json();
  },

  /**
   * WebSocket订阅训练日志
   */
  subscribeLogs(callback: (logs: string[]) => void): () => void {
    const ws = new WebSocket(`ws://localhost:8765/ws/logs`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      callback(data.logs as string[]);
    };
    ws.onerror = (error) => {
      console.error('WebSocket错误:', error);
    };
    return () => ws.close();
  },
};
