import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AxiosError } from 'axios';
import { message } from 'antd';
import request from './request';
import { getRuntimeMode } from '@/utils/env';

vi.mock('antd', () => ({ message: { error: vi.fn() } }));
vi.mock('@/store/useUserStore', () => ({
  useUserStore: { getState: () => ({ token: null, logout: vi.fn() }) },
}));
vi.mock('@/utils/env', () => ({
  getBaseURL: () => '/api',
  getRuntimeMode: vi.fn(() => 'web'),
}));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getRuntimeMode).mockReturnValue('web');
});

describe('请求错误提示', () => {
  it.each(['web', 'desktop'] as const)('%s 模式下主动取消请求不会弹错', async (mode) => {
    vi.mocked(getRuntimeMode).mockReturnValue(mode);
    const controller = new AbortController();
    controller.abort();
    const adapter = vi.fn();

    await expect(request.get('/module4/status', {
      signal: controller.signal, adapter,
    })).rejects.toMatchObject({ code: 'ERR_CANCELED' });

    expect(adapter).not.toHaveBeenCalled();
    expect(message.error).not.toHaveBeenCalled();
  });

  it('真实请求配置错误仍会提示', async () => {
    const error = new AxiosError('Invalid request config');
    await expect(request.get('/module4/status', {
      adapter: () => Promise.reject(error),
    })).rejects.toBe(error);
    expect(message.error).toHaveBeenCalledWith('请求配置错误');
  });

  it('真实网络错误仍会提示', async () => {
    const error = new AxiosError('Network Error', 'ERR_NETWORK', undefined, {});
    await expect(request.get('/module4/status', {
      adapter: () => Promise.reject(error),
    })).rejects.toBe(error);
    expect(message.error).toHaveBeenCalledWith('网络错误，请检查网络连接');
  });
});
