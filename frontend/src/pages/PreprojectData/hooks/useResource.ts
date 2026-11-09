import * as React from 'react';

/** Independent resource with bounded retry, cancellation and explicit manual refresh. */
export function useResource<T>(key: string, enabled: boolean, load: (signal: AbortSignal) => Promise<T>) {
  const [data, setData] = React.useState<T | null>(null);
  const [loadedKey, setLoadedKey] = React.useState('');
  const [error, setError] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [attempt, setAttempt] = React.useState(0);
  React.useEffect(() => {
    setData(null); setError('');
    if (!enabled || !key) { setLoading(false); return undefined; }
    const controller = new AbortController();
    let timer: number | undefined;
    const run = async () => {
      setLoading(true);
      for (let retry = 0; retry < 3; retry += 1) {
        try {
          const value = await load(controller.signal);
          if (!controller.signal.aborted) { setData(value); setLoadedKey(key); setError(''); setLoading(false); }
          return;
        } catch {
          if (controller.signal.aborted) return;
          if (retry === 2) { setError('加载失败，请检查服务后重试。'); setLoading(false); return; }
          setError('加载失败，正在重试；也可手动重试。');
          await new Promise<void>((resolve) => {
            timer = window.setTimeout(resolve, 250 * (2 ** retry));
            controller.signal.addEventListener('abort', () => { window.clearTimeout(timer); resolve(); }, { once: true });
          });
          if (controller.signal.aborted) return;
        }
      }
    };
    void run();
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [key, enabled, load, attempt]);
  return { data: loadedKey === key ? data : null, error, loading, refresh: () => setAttempt((current) => current + 1) };
}
