/**
 * 开发环境调试面板
 * 用于切换运行模式、查看当前状态
 */

import React, { useState, useEffect } from 'react';
import { Card, Radio, Button, Space, Tag, Divider } from 'antd';
import { BugOutlined } from '@ant-design/icons';
import { getRuntimeMode, isDev, isTauri } from '@/utils/env';
import { localNodeApi } from '@/services/api/localNode';

type Mode = 'web' | 'desktop' | 'mock';

export const DebugPanel: React.FC = () => {
  const [mode] = useState<Mode>(getRuntimeMode());
  const [localServiceStatus, setLocalServiceStatus] = useState<boolean>(false);

  // 只在开发环境显示
  if (!isDev()) return null;

  // 检查本地服务状态
  useEffect(() => {
    if (mode === 'desktop') {
      checkLocalService();
      const interval = setInterval(checkLocalService, 5000);
      return () => clearInterval(interval);
    }
  }, [mode]);

  const checkLocalService = async () => {
    const status = await localNodeApi.checkHealth();
    setLocalServiceStatus(status);
  };

  const handleModeChange = (newMode: Mode) => {
    const url = new URL(window.location.href);
    url.searchParams.set('mode', newMode);
    window.location.href = url.toString();
  };

  const getModeColor = (m: Mode): string => {
    switch (m) {
      case 'desktop':
        return 'blue';
      case 'mock':
        return 'orange';
      default:
        return 'green';
    }
  };

  return (
    <Card
      title={
        <Space>
          <BugOutlined />
          <span>调试面板</span>
        </Space>
      }
      size="small"
      style={{
        position: 'fixed',
        bottom: 20,
        right: 20,
        zIndex: 9999,
        width: 320,
        opacity: 0.95,
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* 当前模式显示 */}
        <div>
          <span>当前模式: </span>
          <Tag
            color={getModeColor(mode)}
            style={{ fontSize: 14, padding: '2px 8px' }}
          >
            {mode === 'desktop' && '🖥️ 桌面'}
            {mode === 'web' && '🌐 Web'}
            {mode === 'mock' && '🎭 Mock'}
          </Tag>
        </div>

        {/* Tauri检测 */}
        <div>
          <span>Tauri环境: </span>
          <Tag color={isTauri() ? 'green' : 'red'}>
            {isTauri() ? '是' : '否'}
          </Tag>
        </div>

        {/* 本地服务状态（仅桌面模式） */}
        {mode === 'desktop' && (
          <div>
            <span>本地服务: </span>
            <Tag color={localServiceStatus ? 'green' : 'red'}>
              {localServiceStatus ? '运行中' : '未启动'}
            </Tag>
            <Button
              size="small"
              onClick={checkLocalService}
              style={{ marginLeft: 8 }}
            >
              刷新
            </Button>
          </div>
        )}

        <Divider style={{ margin: '8px 0' }} />

        {/* 模式切换 */}
        <Radio.Group
          value={mode}
          onChange={(e) => handleModeChange(e.target.value)}
        >
          <Radio.Button value="web">Web</Radio.Button>
          <Radio.Button value="desktop">桌面</Radio.Button>
          <Radio.Button value="mock">Mock</Radio.Button>
        </Radio.Group>

        <Divider style={{ margin: '8px 0' }} />

        {/* 快捷操作 */}
        <Space>
          <Button
            size="small"
            danger
            onClick={() => {
              localStorage.clear();
              window.location.reload();
            }}
          >
            清除缓存
          </Button>
          <Button
            size="small"
            onClick={() => {
              console.log('当前状态:', {
                mode: getRuntimeMode(),
                isTauri: isTauri(),
                userAgent: navigator.userAgent,
              });
            }}
          >
            打印状态
          </Button>
        </Space>
      </Space>
    </Card>
  );
};

export default DebugPanel;
