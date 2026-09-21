// Profile 页面 Mock 数据

export interface UserProfile {
  id: string;
  username: string;
  nickname: string;
  avatar: string;
  email: string;
  phone: string;
  bio: string;
  gender: 'male' | 'female' | 'other' | null;
  birthday: string | null;
  location: string;
  website: string;
  createdAt: string;
  lastLoginAt: string;
  realName: string;
  idCard: string;
  verified: boolean;
  verifiedAt: string | null;
}

export const mockUserProfile: UserProfile = {
  id: 'user_001',
  username: 'zhangsan',
  nickname: '张三',
  avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=zhangsan',
  email: 'zhangsan@example.com',
  phone: '138****8888',
  bio: '热爱数据，专注于数据标注与任务处理。欢迎合作！',
  gender: 'male',
  birthday: '1995-06-15',
  location: '北京市朝阳区',
  website: 'https://zhangsan.blog.com',
  createdAt: '2023-01-15 10:30:00',
  lastLoginAt: '2024-01-20 15:45:30',
  realName: '张三',
  idCard: '110101********1234',
  verified: true,
  verifiedAt: '2023-03-20 14:20:00',
};

// 实名认证状态
export interface VerificationStatus {
  status: 'unverified' | 'pending' | 'verified' | 'rejected';
  message?: string;
  submittedAt?: string;
  reviewedAt?: string;
}

export const mockVerificationStatus: VerificationStatus = {
  status: 'verified',
  submittedAt: '2023-03-18 09:00:00',
  reviewedAt: '2023-03-20 14:20:00',
};

// 更新个人资料响应
export const mockUpdateProfileResponse = {
  success: true,
  message: '个人资料更新成功',
  data: mockUserProfile,
};

// 上传头像响应
export const mockUploadAvatarResponse = {
  success: true,
  message: '头像上传成功',
  data: {
    url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=zhangsan&updated=' + Date.now(),
  },
};

// 提交实名认证响应
export const mockSubmitVerificationResponse = {
  success: true,
  message: '实名认证申请已提交，请等待审核',
  data: {
    status: 'pending',
    submittedAt: new Date().toISOString(),
  },
};
