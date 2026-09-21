import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import {
  Download, Monitor, Apple, Terminal, ArrowLeft,
  CheckCircle, Shield, Database, Brain, HardDrive
} from 'lucide-react';

interface PlatformInfo {
  id: string;
  name: string;
  icon: React.FC<{ className?: string }>;
  version: string;
  size: string;
  available: boolean;
  fileName: string;
  requirements: string;
}

const platforms: PlatformInfo[] = [
  {
    id: 'windows',
    name: 'Windows',
    icon: Monitor,
    version: 'v3.0.0',
    size: '167.1 MB',
    available: true,
    fileName: 'FedLearn-Client-Setup-v1.0.0.exe',
    requirements: 'Windows 10/11 64-bit',
  },
  {
    id: 'macos',
    name: 'macOS',
    icon: Apple,
    version: 'v1.0.0',
    size: '92.1 MB',
    available: false,
    fileName: 'fedlearn-client.dmg',
    requirements: 'macOS 12.0 (Monterey) or later',
  },
  {
    id: 'linux',
    name: 'Linux',
    icon: Terminal,
    version: 'v1.0.0',
    size: '78.8 MB',
    available: false,
    fileName: 'fedlearn-client.AppImage',
    requirements: 'Ubuntu 20.04+ / Fedora 36+',
  },
];

const DownloadPage: React.FC = () => {
  const navigate = useNavigate();
  const [hoveredPlatform, setHoveredPlatform] = useState<string | null>(null);

  const handleDownload = (platform: PlatformInfo) => {
    if (!platform.available) {
      message.info(`${platform.name} 版本即将推出，敬请期待`);
      return;
    }
    message.loading({ content: '正在准备下载...', key: 'dl', duration: 2 });
    const link = document.createElement('a');
    link.href = `/downloads/${platform.fileName}`;
    link.download = platform.fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => {
      message.success({ content: '下载已开始，请查看浏览器下载列表', key: 'dl' });
    }, 1500);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-white">
      {/* 顶部导航 */}
      <nav className="bg-white/80 backdrop-blur-md border-b border-gray-100 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span className="text-sm font-medium">返回首页</span>
          </button>
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-green-500 to-emerald-600 text-white flex items-center justify-center text-xs font-bold shadow-md">FL</div>
            <span className="text-sm font-semibold text-gray-900">FedLearn Client</span>
          </div>
        </div>
      </nav>

      {/* 主内容 */}
      <div className="max-w-6xl mx-auto px-6 py-16">
        {/* 标题区 */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-green-50 border border-green-100 text-green-700 text-sm font-medium mb-6">
            <Database className="h-4 w-4" />
            数据提供方专用客户端
          </div>
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4 tracking-tight">
            下载 FedLearn 客户端
          </h1>
          <p className="text-lg text-gray-500 max-w-2xl mx-auto leading-relaxed">
            安装桌面客户端，将您的数据安全地参与联邦学习训练。
            <br />数据始终留在本地，仅上传模型参数。
          </p>
        </div>

        {/* 平台选择卡片 */}
        <div className="grid md:grid-cols-3 gap-6 mb-20">
          {platforms.map((platform) => (
            <div
              key={platform.id}
              className={`relative bg-white rounded-2xl border p-8 transition-all duration-300 cursor-pointer ${
                platform.available
                  ? 'border-green-200 hover:border-green-300 hover:shadow-xl hover:-translate-y-1'
                  : 'border-gray-100 opacity-70'
              }`}
              onMouseEnter={() => setHoveredPlatform(platform.id)}
              onMouseLeave={() => setHoveredPlatform(null)}
              onClick={() => handleDownload(platform)}
            >
              {/* 推荐标签 */}
              {platform.available && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="px-3 py-1 text-xs font-bold text-white bg-gradient-to-r from-green-500 to-emerald-500 rounded-full shadow-lg shadow-green-200/50">
                    可下载
                  </span>
                </div>
              )}

              {/* 即将推出标签 */}
              {!platform.available && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="px-3 py-1 text-xs font-medium text-gray-500 bg-gray-100 rounded-full">
                    即将推出
                  </span>
                </div>
              )}

              <div className="text-center">
                {/* 图标 */}
                <div className={`inline-flex items-center justify-center w-20 h-20 rounded-2xl mb-6 transition-all ${
                  platform.available
                    ? 'bg-gradient-to-br from-green-50 to-emerald-50'
                    : 'bg-gray-50'
                }`}>
                  <platform.icon className={`h-10 w-10 ${
                    platform.available ? 'text-green-600' : 'text-gray-400'
                  }`} />
                </div>

                {/* 平台名称 */}
                <h3 className="text-xl font-bold text-gray-900 mb-1">{platform.name}</h3>
                <p className="text-sm text-gray-500 mb-4">{platform.requirements}</p>

                {/* 版本信息 */}
                <div className="flex items-center justify-center gap-4 text-xs text-gray-400 mb-6">
                  <span>{platform.version}</span>
                  <span className="w-px h-3 bg-gray-200" />
                  <span>{platform.size}</span>
                </div>

                {/* 下载按钮 */}
                {platform.available ? (
                  <button
                    className={`w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-medium transition-all duration-300 ${
                      hoveredPlatform === platform.id
                        ? 'bg-gradient-to-r from-green-500 to-emerald-500 text-white shadow-lg shadow-green-200/50'
                        : 'bg-green-50 text-green-700 hover:bg-green-100'
                    }`}
                  >
                    <Download className="h-4 w-4" />
                    立即下载
                  </button>
                ) : (
                  <div className="w-full py-3 rounded-xl text-sm font-medium text-gray-400 bg-gray-50 text-center">
                    敬请期待
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* 客户端功能介绍 */}
        <div className="mb-20">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-12">客户端核心功能</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              { icon: Shield, title: '数据不出本地', desc: '原始数据始终保留在您的设备上，仅上传加密模型参数' },
              { icon: Brain, title: '智能模型训练', desc: '支持6种预置模型，自动拉取任务对应模型进行本地训练' },
              { icon: HardDrive, title: 'CSV数据加载', desc: '自动解析CSV数据格式，指定路径即可参与联邦训练' },
              { icon: Database, title: '任务浏览参与', desc: '浏览平台推荐任务，一键接受并加入联邦学习训练' },
            ].map((feat, i) => (
              <div key={i} className="bg-white rounded-xl p-6 border border-gray-100 hover:shadow-lg transition-all duration-300">
                <div className="w-10 h-10 rounded-lg bg-green-50 flex items-center justify-center mb-4">
                  <feat.icon className="h-5 w-5 text-green-600" />
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{feat.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{feat.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* 安装步骤 */}
        <div className="bg-white rounded-2xl border border-gray-100 p-10 mb-20">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-10">安装与使用</h2>
          <div className="grid md:grid-cols-4 gap-8">
            {[
              { step: '1', title: '下载安装', desc: '下载对应平台的安装包并完成安装' },
              { step: '2', title: '注册登录', desc: '使用数据提供方账号注册并登录客户端' },
              { step: '3', title: '选择任务', desc: '浏览推荐任务列表，选择匹配的协作任务' },
              { step: '4', title: '开始训练', desc: '指定本地CSV数据路径，客户端自动完成训练' },
            ].map((s, i) => (
              <div key={i} className="text-center">
                <div className="w-12 h-12 rounded-full bg-gradient-to-r from-green-500 to-emerald-500 text-white text-lg font-bold flex items-center justify-center mx-auto mb-4 shadow-lg shadow-green-200/40">
                  {s.step}
                </div>
                <h4 className="font-semibold text-gray-900 mb-2">{s.title}</h4>
                <p className="text-sm text-gray-500">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* 系统要求 */}
        <div className="bg-gray-50 rounded-2xl p-10">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-8">系统要求</h2>
          <div className="grid md:grid-cols-2 gap-8 max-w-3xl mx-auto">
            <div>
              <h3 className="font-semibold text-gray-900 mb-4">最低配置</h3>
              <div className="space-y-3">
                {[
                  '操作系统：Windows 10 64-bit',
                  '处理器：Intel i5 或同等',
                  '内存：4 GB RAM',
                  '硬盘：500 MB 可用空间',
                  'Python 3.9+ (内置)',
                ].map((req, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm text-gray-600">
                    <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />
                    {req}
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-4">推荐配置</h3>
              <div className="space-y-3">
                {[
                  '操作系统：Windows 11 64-bit',
                  '处理器：Intel i7 / AMD Ryzen 7',
                  '内存：8 GB RAM',
                  '硬盘：1 GB 可用空间',
                  'GPU：CUDA 兼容（可选加速）',
                ].map((req, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm text-gray-600">
                    <CheckCircle className="h-4 w-4 text-blue-500 shrink-0" />
                    {req}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 底部 */}
      <footer className="bg-white border-t border-gray-100 py-8">
        <div className="max-w-6xl mx-auto px-6 text-center text-sm text-gray-400">
          FedLearn Platform &copy; {new Date().getFullYear()} — 基于联邦学习的隐私安全数据协作平台
        </div>
      </footer>
    </div>
  );
};

export default DownloadPage;
