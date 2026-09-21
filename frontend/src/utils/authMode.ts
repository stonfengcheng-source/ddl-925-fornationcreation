/**
 * 前端认证模式。
 *
 * 后端默认 AUTH_MODE=passwordless，前端同步默认免密；需要正式密码认证时，
 * 在前端 .env 设置 VITE_AUTH_MODE=password，并在后端设置 AUTH_MODE=password。
 */
export const PASSWORDLESS_AUTH =
  String(import.meta.env.VITE_AUTH_MODE ?? 'passwordless').toLowerCase() !== 'password';

export const DEFAULT_DEV_USERNAME = 'admin';
