// 通知消息 Mock 数据

export type NotificationType = 'system' | 'task' | 'message' | 'reward' | 'security';
export type NotificationPriority = 'high' | 'normal' | 'low';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  content: string;
  isRead: boolean;
  priority: NotificationPriority;
  createdAt: string;
  sender?: {
    id: string;
    name: string;
    avatar?: string;
  };
  actionUrl?: string;
  actionText?: string;
  relatedId?: string;
}

// Mock 通知列表
export const mockNotifications: Notification[] = [
  {
    id: 'NOTIF001',
    type: 'task',
    title: '任务审核通过',
    content: '您提交的数据标注任务 "图片分类项目-批次3" 已通过审核，获得奖励 ¥150.00',
    isRead: false,
    priority: 'normal',
    createdAt: '2024-01-20 15:30:00',
    actionUrl: '/tasks/TASK003',
    actionText: '查看详情',
    relatedId: 'TASK003',
  },
  {
    id: 'NOTIF002',
    type: 'system',
    title: '系统维护通知',
    content: '系统将于今晚 23:00 - 次日 02:00 进行例行维护，期间部分功能可能无法使用，请提前安排您的工作。',
    isRead: false,
    priority: 'high',
    createdAt: '2024-01-20 10:00:00',
  },
  {
    id: 'NOTIF003',
    type: 'reward',
    title: '新用户奖励到账',
    content: '恭喜您获得新用户注册奖励 ¥100.00，已存入您的钱包，可用于提现或任务消费。',
    isRead: true,
    priority: 'normal',
    createdAt: '2024-01-19 09:00:00',
    actionUrl: '/profile/wallet',
    actionText: '查看钱包',
  },
  {
    id: 'NOTIF004',
    type: 'message',
    title: '新消息提醒',
    content: '用户 "李四" 给您发送了一条消息："关于昨天那个标注任务，我有一些疑问想请教..."',
    isRead: false,
    priority: 'normal',
    createdAt: '2024-01-18 16:20:00',
    sender: {
      id: 'USER002',
      name: '李四',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=lisi',
    },
    actionUrl: '/messages/USER002',
    actionText: '回复消息',
  },
  {
    id: 'NOTIF005',
    type: 'security',
    title: '登录提醒',
    content: '您的账户于 2024-01-18 14:30:00 在上海市通过 Chrome 浏览器登录。如非本人操作，请立即修改密码。',
    isRead: true,
    priority: 'high',
    createdAt: '2024-01-18 14:30:00',
    actionUrl: '/profile/security',
    actionText: '查看安全设置',
  },
  {
    id: 'NOTIF006',
    type: 'task',
    title: '新任务推荐',
    content: '根据您的技能标签，我们为您推荐了新任务 "语音识别数据标注"，预计收益 ¥280.00，限时 3 天。',
    isRead: false,
    priority: 'normal',
    createdAt: '2024-01-17 11:00:00',
    actionUrl: '/tasks/TASK004',
    actionText: '查看任务',
    relatedId: 'TASK004',
  },
  {
    id: 'NOTIF007',
    type: 'system',
    title: '平台规则更新',
    content: '《数据标注服务协议》已更新，主要涉及数据隐私保护条款，请您及时查阅。',
    isRead: true,
    priority: 'low',
    createdAt: '2024-01-16 08:00:00',
    actionUrl: '/terms',
    actionText: '查看协议',
  },
  {
    id: 'NOTIF008',
    type: 'reward',
    title: '周度奖励结算',
    content: '您本周共完成 12 个任务，获得周度活跃奖励 ¥50.00，继续加油！',
    isRead: true,
    priority: 'normal',
    createdAt: '2024-01-15 00:00:00',
    actionUrl: '/profile/wallet',
    actionText: '查看明细',
  },
  {
    id: 'NOTIF009',
    type: 'task',
    title: '任务即将截止',
    content: '您承接的任务 "文本情感分析-批次2" 将于 24 小时后截止，请尽快完成提交。',
    isRead: false,
    priority: 'high',
    createdAt: '2024-01-14 10:00:00',
    actionUrl: '/tasks/TASK005',
    actionText: '去完成任务',
    relatedId: 'TASK005',
  },
  {
    id: 'NOTIF010',
    type: 'security',
    title: '密码修改成功',
    content: '您的登录密码已于 2024-01-13 10:30:00 修改成功。如非本人操作，请联系客服。',
    isRead: true,
    priority: 'normal',
    createdAt: '2024-01-13 10:30:00',
  },
  {
    id: 'NOTIF011',
    type: 'message',
    title: '系统公告',
    content: '春节放假通知：平台将于 2024-02-09 至 2024-02-17 放假，期间任务审核可能延迟，请提前安排。',
    isRead: false,
    priority: 'high',
    createdAt: '2024-01-12 09:00:00',
  },
  {
    id: 'NOTIF012',
    type: 'task',
    title: '任务被退回',
    content: '您提交的任务 "图像分割项目" 未通过审核，原因：标注精度不达标。请修改后重新提交。',
    isRead: true,
    priority: 'high',
    createdAt: '2024-01-11 14:00:00',
    actionUrl: '/tasks/TASK006',
    actionText: '查看原因',
    relatedId: 'TASK006',
  },
];

// 通知统计
export const mockNotificationStats = {
  total: 156,
  unread: 5,
  byType: {
    system: 23,
    task: 67,
    message: 18,
    reward: 32,
    security: 16,
  },
};

// 标记已读响应
export const mockMarkAsReadResponse = {
  success: true,
  message: '标记已读成功',
};

// 全部已读响应
export const mockMarkAllAsReadResponse = {
  success: true,
  message: '全部标记已读成功',
  data: {
    markedCount: 5,
  },
};

// 删除通知响应
export const mockDeleteNotificationResponse = {
  success: true,
  message: '删除成功',
};
