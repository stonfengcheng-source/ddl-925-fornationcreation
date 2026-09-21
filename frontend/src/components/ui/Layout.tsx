import * as React from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, ListTodo, User, LogOut, Menu,
  PlusCircle, FolderOpen, Wallet, Bell, ShieldCheck,
  HardDrive, Sparkles, Shield, Settings, Users
} from 'lucide-react';
import { cn } from '@/components/ui/Button';
import { useUserStore, UserRole } from '@/store/useUserStore';
import { getRoleDisplayName } from '@/config/permissions';

interface NavItem {
  icon: React.ElementType;
  label: string;
  href: string;
  roles?: UserRole[]; // undefined = 所有角色可见
}

// 主导航菜单
const mainNavItems: NavItem[] = [
  { icon: LayoutDashboard, label: '工作台', href: '/app/dashboard', roles: ['buyer', 'admin'] },
  { icon: ListTodo, label: '任务大厅', href: '/app/tasks', roles: ['buyer', 'admin'] },
  { icon: PlusCircle, label: '发布任务', href: '/app/tasks/publish', roles: ['buyer', 'admin'] },
  { icon: FolderOpen, label: '我的任务', href: '/app/my-tasks', roles: ['buyer', 'admin'] },
];

// 数据管理菜单（仅管理员在Web端可见，提供方功能已迁移至桌面客户端）
const dataNavItems: NavItem[] = [
  { icon: HardDrive, label: '我的数据资产', href: '/app/data-assets', roles: ['admin'] },
  { icon: Sparkles, label: '推荐任务', href: '/app/matching', roles: ['admin'] },
  { icon: ShieldCheck, label: '质量规则', href: '/app/quality-rules', roles: ['admin'] },
  { icon: HardDrive, label: '边缘节点', href: '/app/edge-nodes', roles: ['admin'] },
];

// 隐私保护菜单
const privacyNavItems: NavItem[] = [
  { icon: Shield, label: '隐私预算', href: '/app/privacy-budget', roles: ['buyer', 'admin'] },
];

// 个人中心菜单
const userNavItems: NavItem[] = [
  { icon: User, label: '个人资料', href: '/app/profile', roles: ['buyer', 'admin'] },
  { icon: Wallet, label: '我的钱包', href: '/app/profile/wallet', roles: ['buyer', 'admin'] },
  { icon: Bell, label: '消息通知', href: '/app/notifications', roles: ['buyer', 'admin'] },
];

// 管理后台菜单
const adminNavItems: NavItem[] = [
  { icon: Settings, label: '管理总览', href: '/app/admin', roles: ['admin'] },
  { icon: ListTodo, label: '任务管理', href: '/app/admin/tasks', roles: ['admin'] },
  { icon: Users, label: '用户管理', href: '/app/admin/users', roles: ['admin'] },
];

// 根据角色过滤导航项
const filterNavItems = (items: NavItem[], role: UserRole | undefined): NavItem[] => {
  return items.filter((item) => !item.roles || (role && item.roles.includes(role)));
};

export function Layout() {
  const [isSidebarOpen, setIsSidebarOpen] = React.useState(true);
  const location = useLocation();
  const navigate = useNavigate();
  const logout = useUserStore((state) => state.logout);
  const user = useUserStore((state) => state.user);
  const role = user?.role;

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

  // 根据角色过滤菜单项
  const filteredMainNavItems = React.useMemo(() => filterNavItems(mainNavItems, role), [role]);
  const filteredDataNavItems = React.useMemo(() => filterNavItems(dataNavItems, role), [role]);
  const filteredPrivacyNavItems = React.useMemo(() => filterNavItems(privacyNavItems, role), [role]);
  const filteredUserNavItems = React.useMemo(() => filterNavItems(userNavItems, role), [role]);
  const filteredAdminNavItems = React.useMemo(() => filterNavItems(adminNavItems, role), [role]);

  // 计算当前激活的导航项（最长前缀匹配，避免 /tasks 和 /tasks/publish 同时高亮）
  const allNavItems = [
    ...filteredMainNavItems,
    ...filteredDataNavItems,
    ...filteredPrivacyNavItems,
    ...filteredUserNavItems,
    ...filteredAdminNavItems,
  ];
  const activeHref = React.useMemo(() => {
    let best = '';
    for (const item of allNavItems) {
      if (location.pathname === item.href || location.pathname.startsWith(`${item.href}/`)) {
        if (item.href.length > best.length) {
          best = item.href;
        }
      }
    }
    return best;
  }, [location.pathname]);

  const isNavActive = (href: string) => href === activeHref;

  return (
    <div className="flex h-screen w-full bg-background overflow-hidden font-sans text-text">
      {/* Sidebar - Notion Style (Light Gray) */}
      <aside
        className={cn(
          "flex flex-col border-r border-border-light bg-background-secondary transition-all duration-300 ease-in-out",
          isSidebarOpen ? "w-64" : "w-16"
        )}
      >
        <div className="flex h-12 items-center px-3 mt-2">
          <button
            onClick={toggleSidebar}
            className="p-1 hover:bg-background-tertiary rounded-sm transition-colors text-text-secondary hover:text-text"
          >
            <div className={cn("flex items-center gap-2 font-medium overflow-hidden", !isSidebarOpen && "hidden")}>
              <div className="h-5 w-5 rounded bg-text-primary text-white flex items-center justify-center text-[10px] font-bold">
                N
              </div>
              <span className="truncate text-sm">Data Task Platform</span>
            </div>
            {!isSidebarOpen && <Menu className="h-4 w-4" />}
          </button>
        </div>

        <nav className="flex-1 space-y-4 p-2 overflow-y-auto">
          {/* 主导航 */}
          <div className="space-y-0.5">
            {isSidebarOpen && filteredMainNavItems.length > 0 && (
              <div className="px-3 py-1 text-xs font-medium text-text-secondary/60">工作台</div>
            )}
            {filteredMainNavItems.map((item) => {
              const active = isNavActive(item.href);
              return (
                <button
                  key={item.href}
                  onClick={() => navigate(item.href)}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-sm px-3 py-1.5 text-sm transition-colors",
                    active
                      ? "bg-background-tertiary text-text font-medium"
                      : "text-text-secondary hover:bg-background-tertiary hover:text-text",
                    !isSidebarOpen && "justify-center px-2"
                  )}
                  title={!isSidebarOpen ? item.label : undefined}
                >
                  <item.icon className={cn("h-4 w-4 shrink-0", active ? "text-text" : "text-text-secondary")} />
                  {isSidebarOpen && <span>{item.label}</span>}
                </button>
              );
            })}
          </div>

          {/* 数据管理 */}
          {filteredDataNavItems.length > 0 && (
            <div className="space-y-0.5">
              {isSidebarOpen && <div className="px-3 py-1 text-xs font-medium text-text-secondary/60">数据管理</div>}
              {filteredDataNavItems.map((item) => {
                const active = isNavActive(item.href);
                return (
                  <button
                    key={item.href}
                    onClick={() => navigate(item.href)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-sm px-3 py-1.5 text-sm transition-colors",
                      active
                        ? "bg-background-tertiary text-text font-medium"
                        : "text-text-secondary hover:bg-background-tertiary hover:text-text",
                      !isSidebarOpen && "justify-center px-2"
                    )}
                    title={!isSidebarOpen ? item.label : undefined}
                  >
                    <item.icon className={cn("h-4 w-4 shrink-0", active ? "text-text" : "text-text-secondary")} />
                    {isSidebarOpen && <span>{item.label}</span>}
                  </button>
                );
              })}
            </div>
          )}

          {/* 隐私保护 */}
          {filteredPrivacyNavItems.length > 0 && (
            <div className="space-y-0.5">
              {isSidebarOpen && <div className="px-3 py-1 text-xs font-medium text-text-secondary/60">隐私保护</div>}
              {filteredPrivacyNavItems.map((item) => {
                const active = isNavActive(item.href);
                return (
                  <button
                    key={item.href}
                    onClick={() => navigate(item.href)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-sm px-3 py-1.5 text-sm transition-colors",
                      active
                        ? "bg-background-tertiary text-text font-medium"
                        : "text-text-secondary hover:bg-background-tertiary hover:text-text",
                      !isSidebarOpen && "justify-center px-2"
                    )}
                    title={!isSidebarOpen ? item.label : undefined}
                  >
                    <item.icon className={cn("h-4 w-4 shrink-0", active ? "text-text" : "text-text-secondary")} />
                    {isSidebarOpen && <span>{item.label}</span>}
                  </button>
                );
              })}
            </div>
          )}

          {/* 个人中心 */}
          {filteredUserNavItems.length > 0 && (
            <div className="space-y-0.5">
              {isSidebarOpen && <div className="px-3 py-1 text-xs font-medium text-text-secondary/60">个人中心</div>}
              {filteredUserNavItems.map((item) => {
                const active = isNavActive(item.href);
                return (
                  <button
                    key={item.href}
                    onClick={() => navigate(item.href)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-sm px-3 py-1.5 text-sm transition-colors",
                      active
                        ? "bg-background-tertiary text-text font-medium"
                        : "text-text-secondary hover:bg-background-tertiary hover:text-text",
                      !isSidebarOpen && "justify-center px-2"
                    )}
                    title={!isSidebarOpen ? item.label : undefined}
                  >
                    <item.icon className={cn("h-4 w-4 shrink-0", active ? "text-text" : "text-text-secondary")} />
                    {isSidebarOpen && <span>{item.label}</span>}
                  </button>
                );
              })}
            </div>
          )}

          {/* 管理后台 */}
          {filteredAdminNavItems.length > 0 && (
            <div className="space-y-0.5">
              {isSidebarOpen && <div className="px-3 py-1 text-xs font-medium text-text-secondary/60">系统管理</div>}
              {filteredAdminNavItems.map((item) => {
                const active = isNavActive(item.href);
                return (
                  <button
                    key={item.href}
                    onClick={() => navigate(item.href)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-sm px-3 py-1.5 text-sm transition-colors",
                      active
                        ? "bg-background-tertiary text-text font-medium"
                        : "text-text-secondary hover:bg-background-tertiary hover:text-text",
                      !isSidebarOpen && "justify-center px-2"
                    )}
                    title={!isSidebarOpen ? item.label : undefined}
                  >
                    <item.icon className={cn("h-4 w-4 shrink-0", active ? "text-text" : "text-text-secondary")} />
                    {isSidebarOpen && <span>{item.label}</span>}
                  </button>
                );
              })}
            </div>
          )}
        </nav>

        <div className="border-t border-border-light p-2">
          <button
            onClick={() => { logout(); navigate('/'); }}
            className={cn(
              "flex w-full items-center gap-3 rounded-sm px-3 py-1.5 text-sm text-text-secondary hover:bg-background-tertiary hover:text-text transition-colors",
              !isSidebarOpen && "justify-center px-2"
            )}
            title={!isSidebarOpen ? "退出登录" : undefined}
          >
            <LogOut className="h-4 w-4 shrink-0" />
            {isSidebarOpen && <span>退出登录</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-background">
        {/* Header - Minimalist Notion Style */}
        <header className="flex h-12 items-center justify-between px-6 sticky top-0 z-10 bg-background/80 backdrop-blur-sm">
          <div className="flex items-center gap-4">
             {/* Breadcrumbs or Title could go here */}
             <div className="flex items-center text-sm text-text-secondary">
                <span className="hover:underline cursor-pointer">工作台</span>
                <span className="mx-2">/</span>
                <span className="text-text font-medium">
                  {allNavItems.find(i => i.href === activeHref)?.label || '页面'}
                </span>
             </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-text-secondary hover:bg-background-secondary px-2 py-1 rounded cursor-pointer transition-colors">
              <div className="h-5 w-5 rounded-full bg-accent-purple text-white flex items-center justify-center text-xs font-medium">
                {user?.username?.charAt(0).toUpperCase() || 'U'}
              </div>
              <div className="flex flex-col items-start">
                <span className="text-xs font-medium text-text">{user?.username || '用户'}</span>
                <span className="text-[10px] text-text-secondary/70">{getRoleDisplayName(role)}</span>
              </div>
            </div>
          </div>
        </header>

        {/* Scrollable Content Area */}
        <div className="flex-1 overflow-auto px-4 sm:px-6 lg:px-10 py-6 max-w-6xl mx-auto w-full">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
