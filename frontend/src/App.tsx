import React from 'react';
import { BrowserRouter, useRoutes } from 'react-router-dom';
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
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
};

export default App;