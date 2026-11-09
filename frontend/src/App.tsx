import React from 'react';
import { BrowserRouter, useRoutes } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { routes } from '@/config/routes';

/**
 * 路由渲染组件
 */
const AppRoutes: React.FC = () => {
  const element = useRoutes(routes);
  return element;
};

/**
 * 应用根组件
 */
const App: React.FC = () => {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1e6fff',
          colorBgLayout: '#f5f7fb',
          colorBorder: '#e7edf5',
          borderRadius: 10,
          fontFamily: 'Inter, "PingFang SC", "Microsoft YaHei", sans-serif',
        },
      }}
    >
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
