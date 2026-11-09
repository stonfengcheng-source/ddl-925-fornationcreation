import { afterEach, describe, expect, it, vi } from 'vitest';
import { getBaseURL } from './env';

afterEach(() => vi.unstubAllEnvs());

describe('platform API base URL', () => {
  it('routes desktop platform requests to the FastAPI service, not the local-node service', () => {
    expect(getBaseURL('desktop')).toBe('http://127.0.0.1:8000/api');
  });

  it('keeps web and mock requests on the same-origin API path', () => {
    expect(getBaseURL('web')).toBe('/api');
    expect(getBaseURL('mock')).toBe('/api');
  });

  it('allows the desktop platform API address to be configured', () => {
    vi.stubEnv('VITE_PLATFORM_API_BASE_URL', 'http://127.0.0.1:8100/api');
    expect(getBaseURL('desktop')).toBe('http://127.0.0.1:8100/api');
  });
});
