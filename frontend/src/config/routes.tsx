import { RouteObject, Navigate } from 'react-router-dom';
import BasicLayout from '@/layouts/BasicLayout';
import AuthGuard from '@/components/common/AuthGuard';
import { Permission } from '@/config/permissions';
import LandingPage from '@/pages/Landing';
import DownloadPage from '@/pages/Download';
import AdminLogin from '@/pages/Auth/AdminLogin';
import TaskList from '@/pages/Tasks';
import TaskDetail from '@/pages/TaskDetail';
import TaskPublish from '@/pages/TaskPublish';
import MyTasks from '@/pages/MyTasks';
import QualityReport from '@/pages/marketplace/QualityReport';
import TrainingMonitor from '@/pages/federated/TrainingMonitor';
import RevenueShare from '@/pages/federated/RevenueShare';
import PrivacyBudgetDashboard from '@/pages/PrivacyBudget';
import QualityRuleEditor from '@/pages/quality-rules/Editor';
import QualityRuleList from '@/pages/quality-rules';
import NodeList from '@/pages/edge-nodes/NodeList';
import NodeRegister from '@/pages/edge-nodes/NodeRegister';
import NodeDetail from '@/pages/edge-nodes/NodeDetail';
import Dashboard from '@/pages/Dashboard';
// 数据资产模块（新）
import DataAssetList from '@/pages/DataProfile';
import DataAssetCreate from '@/pages/DataProfile/Create';
import MatchingTasks from '@/pages/Matching';
import Profile from '@/pages/Profile';
import Security from '@/pages/Profile/Security';
import Wallet from '@/pages/Profile/Wallet';
import Notifications from '@/pages/Notifications';
import AdminDashboard from '@/pages/Admin/Dashboard';
import UserManagement from '@/pages/Admin/UserManagement';
import TaskManagement from '@/pages/Admin/TaskManagement';

// 错误页面
const Forbidden = () => (
  <div style={{ textAlign: 'center', padding: '100px 20px' }}>
    <h1 style={{ fontSize: 120, color: '#f0f0f0', margin: 0 }}>403</h1>
    <h2 style={{ marginTop: -20 }}>无权限访问</h2>
    <p style={{ color: '#8c8c8c' }}>您没有权限访问此页面</p>
    <a href="/app/dashboard" style={{ color: '#1890ff' }}>返回工作台</a>
  </div>
);

const NotFound = () => (
  <div style={{ textAlign: 'center', padding: '100px 20px' }}>
    <h1 style={{ fontSize: 120, color: '#f0f0f0', margin: 0 }}>404</h1>
    <h2 style={{ marginTop: -20 }}>页面不存在</h2>
    <p style={{ color: '#8c8c8c' }}>您访问的页面不存在或已被移除</p>
    <a href="/" style={{ color: '#1890ff' }}>返回首页</a>
  </div>
);

/**
 * 路由配置
 * 按模块组织路由结构
 */
export const routes: RouteObject[] = [
  // 展示首页（含底部买方登录/注册）
  {
    path: '/',
    element: <LandingPage />,
  },

  // 客户端下载页（数据提供方）
  {
    path: '/download',
    element: <DownloadPage />,
  },

  // 管理员登录
  {
    path: '/admin',
    element: <AdminLogin />,
  },

  // 主布局路由（需要认证）
  {
    path: '/app',
    element: (
      <AuthGuard>
        <BasicLayout />
      </AuthGuard>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/app/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: <Dashboard />,
      },

      // 任务模块
      {
        path: 'tasks',
        children: [
          {
            index: true,
            element: <TaskList />,
          },
          {
            path: 'publish',
            element: (
              <AuthGuard requiredPermission={'task:publish' as Permission}>
                <TaskPublish />
              </AuthGuard>
            ),
          },
          {
            path: ':taskId',
            element: <TaskDetail />,
          },
        ],
      },
      {
        path: 'my-tasks',
        element: <MyTasks />,
      },

      // 数据资产模块（新）- 需要 dataasset:view 权限
      {
        path: 'data-assets',
        children: [
          {
            index: true,
            element: (
              <AuthGuard requiredPermission={'dataasset:view' as Permission}>
                <DataAssetList />
              </AuthGuard>
            ),
          },
          {
            path: 'create',
            element: (
              <AuthGuard requiredPermission={'dataasset:create' as Permission}>
                <DataAssetCreate />
              </AuthGuard>
            ),
          },
        ],
      },
      // 推荐任务（新）- 需要 task:join 权限（provider 视角）
      {
        path: 'matching',
        element: (
          <AuthGuard requiredPermission={'task:join' as Permission}>
            <MatchingTasks />
          </AuthGuard>
        ),
      },

      // 联邦学习模块
      {
        path: 'federated',
        children: [
          {
            path: 'training/:taskId',
            element: <TrainingMonitor />,
          },
          {
            path: 'revenue/:taskId',
            element: <RevenueShare />,
          },
        ],
      },

      // 隐私预算模块
      {
        path: 'privacy-budget',
        element: <PrivacyBudgetDashboard />,
      },

      // 边缘节点模块
      {
        path: 'edge-nodes',
        children: [
          {
            index: true,
            element: <NodeList />,
          },
          {
            path: 'register',
            element: (
              <AuthGuard requiredPermission={'node:register' as Permission}>
                <NodeRegister />
              </AuthGuard>
            ),
          },
          {
            path: ':nodeId',
            element: <NodeDetail />,
          },
        ],
      },

      // 数据市场模块
      {
        path: 'marketplace',
        children: [
          {
            path: 'quality/:dataId',
            element: <QualityReport />,
          },
        ],
      },

      // 质量规则模块 - 需要 qualityrule:manage 权限
      {
        path: 'quality-rules',
        children: [
          {
            index: true,
            element: (
              <AuthGuard requiredPermission={'qualityrule:manage' as Permission}>
                <QualityRuleList />
              </AuthGuard>
            ),
          },
          {
            path: 'editor',
            element: (
              <AuthGuard requiredPermission={'qualityrule:manage' as Permission}>
                <QualityRuleEditor />
              </AuthGuard>
            ),
          },
          {
            path: 'editor/:ruleId',
            element: (
              <AuthGuard requiredPermission={'qualityrule:manage' as Permission}>
                <QualityRuleEditor />
              </AuthGuard>
            ),
          },
        ],
      },

      // 用户中心模块
      {
        path: 'profile',
        children: [
          {
            index: true,
            element: <Profile />,
          },
          {
            path: 'security',
            element: <Security />,
          },
          {
            path: 'wallet',
            element: <Wallet />,
          },
        ],
      },
      {
        path: 'notifications',
        element: <Notifications />,
      },

      // 管理后台模块（需要管理员权限）
      {
        path: 'admin',
        element: (
          <AuthGuard requiredRole="admin">
            <AdminDashboard />
          </AuthGuard>
        ),
      },
      {
        path: 'admin/users',
        element: (
          <AuthGuard requiredRole="admin">
            <UserManagement />
          </AuthGuard>
        ),
      },
      {
        path: 'admin/tasks',
        element: (
          <AuthGuard requiredRole="admin">
            <TaskManagement />
          </AuthGuard>
        ),
      },
    ],
  },

  // 403 页面
  {
    path: '/403',
    element: <Forbidden />,
  },

  // 404 页面
  {
    path: '*',
    element: <NotFound />,
  },
];

export default routes;
