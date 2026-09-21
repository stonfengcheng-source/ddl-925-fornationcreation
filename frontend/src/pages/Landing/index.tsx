import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { message } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { useUserStore } from '@/store/useUserStore';
import { DEFAULT_DEV_USERNAME, PASSWORDLESS_AUTH } from '@/utils/authMode';
import {
  Shield, Database, Brain, BarChart3, Users, Download,
  ChevronDown, ArrowRight, Lock, Zap, Globe,
  CheckCircle, Star, TrendingUp, Server, Eye, EyeOff
} from 'lucide-react';

/* ─── Scroll animation hook ─── */
function useScrollReveal() {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); obs.disconnect(); } },
      { threshold: 0.12, rootMargin: '0px 0px -60px 0px' },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return { ref, visible };
}

function RevealSection({ children, className = '', delay = 0, direction = 'up' }: {
  children: React.ReactNode; className?: string; delay?: number; direction?: 'up' | 'left' | 'right';
}) {
  const { ref, visible } = useScrollReveal();
  const initialTransform = direction === 'left' ? 'translateX(-60px)'
    : direction === 'right' ? 'translateX(60px)' : 'translateY(60px)';
  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translate(0)' : initialTransform,
        transition: `opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms, transform 0.8s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}

/* ─── Main Landing Page ─── */
const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useUserStore();
  const [scrollY, setScrollY] = useState(0);

  // Auth form state
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [loading, setLoading] = useState(false);
  const [showPwd, setShowPwd] = useState(false);
  const [form, setForm] = useState({ username: DEFAULT_DEV_USERNAME, password: '', email: '', confirmPassword: '' });
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    const h = () => setScrollY(window.scrollY);
    window.addEventListener('scroll', h, { passive: true });
    return () => window.removeEventListener('scroll', h);
  }, []);

  const scrollTo = useCallback((id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm(p => ({ ...p, [name]: value }));
    if (errors[name]) setErrors(p => ({ ...p, [name]: '' }));
  };

  /* ── Login ── */
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!form.username.trim()) errs.username = '请输入用户名';
    if (!PASSWORDLESS_AUTH && !form.password) errs.password = '请输入密码';
    if (Object.keys(errs).length) { setErrors(errs); return; }

    setLoading(true);
    try {
      const request = (await import('@/services/request')).default;
      const res: any = await request.post('/auth/login', {
        username: form.username,
        password: PASSWORDLESS_AUTH ? '' : form.password,
        source: 'web',
      });
      const u = res.user || res.data?.user;
      const t = res.token || res.data?.token;
      login({ userId: u.id, username: u.username, email: u.email || '', role: u.user_type as any }, t);
      message.success('登录成功');
      navigate('/app/dashboard');
    } catch (err: any) {
      message.error(err?.response?.data?.detail || err?.response?.data?.error?.message || '登录失败');
    } finally { setLoading(false); }
  };

  /* ── Register ── */
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    const errs: Record<string, string> = {};
    if (!form.username.trim()) errs.username = '请输入用户名';
    if (!form.email.trim()) errs.email = '请输入邮箱';
    if (!PASSWORDLESS_AUTH && !form.password) errs.password = '请输入密码';
    if (!PASSWORDLESS_AUTH && form.password !== form.confirmPassword) errs.confirmPassword = '两次密码不一致';
    if (Object.keys(errs).length) { setErrors(errs); return; }

    setLoading(true);
    try {
      const request = (await import('@/services/request')).default;
      await request.post('/auth/register', {
        username: form.username,
        email: form.email,
        password: PASSWORDLESS_AUTH ? '' : form.password,
        user_type: 'buyer',
      });
      message.success('注册成功，请登录');
      setAuthMode('login');
      setForm(p => ({ ...p, confirmPassword: '', email: '' }));
    } catch (err: any) {
      message.error(err?.response?.data?.detail || '注册失败');
    } finally { setLoading(false); }
  };

  const navOpaque = scrollY > 60;

  return (
    <div className="w-full bg-white">

      {/* ════════ 固定顶部导航栏 ════════ */}
      <nav
        className="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
        style={{
          background: navOpaque ? 'rgba(255,255,255,0.95)' : 'transparent',
          backdropFilter: navOpaque ? 'blur(16px)' : 'none',
          boxShadow: navOpaque ? '0 1px 3px rgba(0,0,0,0.06)' : 'none',
        }}
      >
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => scrollTo('hero')}>
            <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 text-white flex items-center justify-center text-sm font-bold shadow-lg shadow-blue-200/40">FL</div>
            <span className="text-lg font-semibold text-gray-900 tracking-tight hidden sm:block">FedLearn Platform</span>
          </div>

          <div className="flex items-center gap-2">
            {/* 买方 → 滚动到底部登录 */}
            <button
              onClick={() => scrollTo('auth')}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            >
              需求方登录
            </button>
            {/* 数据提供方 → 下载页 */}
            <button
              onClick={() => navigate('/download')}
              className="hidden sm:flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-gray-700 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors"
            >
              <Download className="h-4 w-4" />
              数据提供方
            </button>
            {/* 管理员 → /admin */}
            <button
              onClick={() => navigate('/admin')}
              className="hidden sm:flex items-center gap-1.5 px-4 py-2 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
            >
              <Shield className="h-4 w-4" />
              管理员
            </button>
          </div>
        </div>
      </nav>

      {/* ════════ 滚动内容 ════════ */}
      <div className="scroll-smooth">

        {/* ═══ Section 1: Hero ═══ */}
        <section id="hero" className="relative min-h-screen flex items-center justify-center overflow-hidden">
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute top-1/4 -left-40 w-[500px] h-[500px] bg-blue-100 rounded-full mix-blend-multiply blur-3xl opacity-40 animate-pulse" />
            <div className="absolute top-1/3 -right-40 w-[500px] h-[500px] bg-purple-100 rounded-full mix-blend-multiply blur-3xl opacity-40 animate-pulse" style={{ animationDelay: '2s' }} />
            <div className="absolute -bottom-40 left-1/3 w-[500px] h-[500px] bg-indigo-100 rounded-full mix-blend-multiply blur-3xl opacity-30 animate-pulse" style={{ animationDelay: '4s' }} />
          </div>

          <div className="relative z-10 max-w-5xl mx-auto px-6 text-center">
            <RevealSection>
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-50 border border-blue-100 text-blue-700 text-sm font-medium mb-8">
                <Zap className="h-4 w-4" />
                基于联邦学习的隐私安全数据协作平台
              </div>
            </RevealSection>

            <RevealSection delay={150}>
              <h1 className="text-5xl md:text-7xl font-bold text-gray-900 leading-tight mb-6 tracking-tight">
                让数据协作
                <br />
                <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent">
                  安全无忧
                </span>
              </h1>
            </RevealSection>

            <RevealSection delay={300}>
              <p className="text-xl md:text-2xl text-gray-500 max-w-3xl mx-auto mb-12 leading-relaxed">
                数据不出本地，模型共享训练。多方数据价值释放，
                <br className="hidden md:block" />
                差分隐私保护 + 智能语义匹配 + 自动贡献度评估。
              </p>
            </RevealSection>

            <RevealSection delay={450}>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
                <button
                  onClick={() => scrollTo('auth')}
                  className="group flex items-center gap-2 px-8 py-3.5 text-base font-medium text-white bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl hover:shadow-xl hover:shadow-blue-200/50 transition-all duration-300 hover:-translate-y-0.5"
                >
                  需求方入口
                  <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
                </button>
                <button
                  onClick={() => navigate('/download')}
                  className="group flex items-center gap-2 px-8 py-3.5 text-base font-medium text-gray-700 bg-white border border-gray-200 rounded-xl hover:border-gray-300 hover:shadow-lg transition-all duration-300 hover:-translate-y-0.5"
                >
                  <Download className="h-5 w-5" />
                  数据提供方客户端
                </button>
              </div>
            </RevealSection>

            <RevealSection delay={600}>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-3xl mx-auto">
                {[
                  { value: '6+', label: '内置模型', icon: Brain },
                  { value: 'ε-DP', label: '差分隐私', icon: Shield },
                  { value: '100%', label: '数据不出本地', icon: Lock },
                  { value: '实时', label: '训练监控', icon: BarChart3 },
                ].map((stat, i) => (
                  <div key={i} className="text-center">
                    <div className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-gray-50 mb-2">
                      <stat.icon className="h-5 w-5 text-blue-600" />
                    </div>
                    <div className="text-2xl font-bold text-gray-900">{stat.value}</div>
                    <div className="text-sm text-gray-500">{stat.label}</div>
                  </div>
                ))}
              </div>
            </RevealSection>
          </div>

          <button
            onClick={() => scrollTo('problem')}
            className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 text-gray-400 hover:text-gray-600 transition-colors animate-bounce"
          >
            <span className="text-xs">向下滚动</span>
            <ChevronDown className="h-5 w-5" />
          </button>
        </section>

        {/* ═══ Section 2: 我们解决什么问题 ═══ */}
        <section id="problem" className="py-28 bg-gray-50/60">
          <div className="max-w-6xl mx-auto px-6">
            <RevealSection>
              <div className="text-center mb-16">
                <span className="inline-block px-3 py-1 text-xs font-semibold text-red-600 bg-red-50 rounded-full mb-4 tracking-wide">PROBLEM</span>
                <h2 className="text-3xl md:text-5xl font-bold text-gray-900 mb-4">传统数据协作的困境</h2>
                <p className="text-lg text-gray-500 max-w-2xl mx-auto">
                  在数据孤岛时代，企业面临着数据共享与隐私保护之间的两难抉择
                </p>
              </div>
            </RevealSection>

            <div className="grid md:grid-cols-3 gap-8">
              {[
                { icon: Lock, title: '数据隐私泄露', desc: '传统数据共享需要将原始数据传输给第三方，面临严重的隐私泄露和合规风险', color: 'red' },
                { icon: Database, title: '数据孤岛', desc: '各机构数据彼此隔离，无法联合利用多方数据训练更精准的AI模型', color: 'orange' },
                { icon: Star, title: '价值分配不公', desc: '数据贡献难以量化，缺乏公平透明的利益分配机制，各方参与积极性低', color: 'yellow' },
              ].map((item, i) => (
                <RevealSection key={i} delay={i * 150}>
                  <div className="bg-white rounded-2xl p-8 border border-gray-100 hover:shadow-xl transition-all duration-300 hover:-translate-y-1 h-full">
                    <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-5 ${
                      item.color === 'red' ? 'bg-red-50' : item.color === 'orange' ? 'bg-orange-50' : 'bg-yellow-50'
                    }`}>
                      <item.icon className={`h-7 w-7 ${
                        item.color === 'red' ? 'text-red-500' : item.color === 'orange' ? 'text-orange-500' : 'text-yellow-500'
                      }`} />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-3">{item.title}</h3>
                    <p className="text-gray-500 leading-relaxed">{item.desc}</p>
                  </div>
                </RevealSection>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ Section 3: 我们的创新解决方案 ═══ */}
        <section id="solutions" className="py-28 bg-white">
          <div className="max-w-6xl mx-auto px-6">
            <RevealSection>
              <div className="text-center mb-16">
                <span className="inline-block px-3 py-1 text-xs font-semibold text-blue-600 bg-blue-50 rounded-full mb-4 tracking-wide">SOLUTIONS</span>
                <h2 className="text-3xl md:text-5xl font-bold text-gray-900 mb-4">四大创新解决方案</h2>
                <p className="text-lg text-gray-500 max-w-2xl mx-auto">
                  从隐私保护到价值评估，全链路创新让数据协作安全、高效、公平
                </p>
              </div>
            </RevealSection>

            <div className="space-y-16">
              {[
                {
                  icon: Shield, badge: '创新 1',
                  title: '联邦学习 — 数据不出本地',
                  desc: '基于Flower框架实现FedAvg联邦聚合，原始数据始终保留在数据提供方本地设备上，仅交换加密后的模型参数梯度。服务端永远无法接触任何原始数据。',
                  highlights: ['原始数据零传输', 'Flower框架 + FedAvg聚合', '支持6种模型模板', '分类与回归任务全覆盖'],
                  gradient: 'from-blue-500 to-cyan-500',
                },
                {
                  icon: Lock, badge: '创新 2',
                  title: '中心化差分隐私 (Central DP)',
                  desc: '在模型聚合阶段注入经数学校准的高斯噪声，提供可量化的 ε-差分隐私保障。支持固定裁剪与自适应裁剪两种策略，隐私预算消耗实时可视化追踪。',
                  highlights: ['ε-δ 差分隐私保障', '固定裁剪 + 自适应裁剪', '隐私预算仪表盘', '噪声量级可精确调控'],
                  gradient: 'from-purple-500 to-pink-500',
                },
                {
                  icon: Brain, badge: '创新 3',
                  title: '语义匹配引擎',
                  desc: '基于pgvector向量数据库的多因子匹配算法，自动为任务推荐最合适的数据提供方。综合语义相似度、标签匹配和数据量三个维度进行加权评分。',
                  highlights: ['向量嵌入 + 余弦相似度', '多因子加权评分', '自动推荐最优数据集', '支持多LLM嵌入服务'],
                  gradient: 'from-indigo-500 to-blue-500',
                },
                {
                  icon: TrendingUp, badge: '创新 4',
                  title: '公平贡献度评估与收益分配',
                  desc: '训练前预评估 + 训练后精确计算双阶段贡献度评估体系。按数据量(40%)、数据质量(30%)、计算贡献(20%)、时效性(10%)四个维度综合打分，驱动公平的奖励池分配。',
                  highlights: ['数据量 40% 权重', '数据质量 30% 权重', '计算贡献 20% 权重', '自动结算到钱包'],
                  gradient: 'from-green-500 to-emerald-500',
                },
              ].map((sol, i) => (
                <RevealSection key={i}>
                  <div className={`flex flex-col ${i % 2 === 1 ? 'md:flex-row-reverse' : 'md:flex-row'} gap-10 items-center`}>
                    {/* 左侧：图标+亮点 */}
                    <div className="flex-1">
                      <span className={`inline-block px-3 py-1 text-xs font-bold text-white bg-gradient-to-r ${sol.gradient} rounded-full mb-4`}>
                        {sol.badge}
                      </span>
                      <h3 className="text-2xl md:text-3xl font-bold text-gray-900 mb-4">{sol.title}</h3>
                      <p className="text-gray-500 leading-relaxed mb-6">{sol.desc}</p>
                      <div className="grid grid-cols-2 gap-3">
                        {sol.highlights.map((h, j) => (
                          <div key={j} className="flex items-center gap-2 text-sm text-gray-700">
                            <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />
                            {h}
                          </div>
                        ))}
                      </div>
                    </div>
                    {/* 右侧：装饰卡片 */}
                    <div className="flex-1 flex justify-center">
                      <div className={`w-64 h-64 rounded-3xl bg-gradient-to-br ${sol.gradient} p-1 shadow-2xl`} style={{ boxShadow: `0 25px 60px -12px rgba(0,0,0,0.15)` }}>
                        <div className="w-full h-full rounded-[22px] bg-white/90 backdrop-blur flex items-center justify-center">
                          <sol.icon className="h-24 w-24 text-gray-300" strokeWidth={1} />
                        </div>
                      </div>
                    </div>
                  </div>
                </RevealSection>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ Section 4: 技术架构 ═══ */}
        <section id="architecture" className="py-28 bg-gray-50/60">
          <div className="max-w-6xl mx-auto px-6">
            <RevealSection>
              <div className="text-center mb-16">
                <span className="inline-block px-3 py-1 text-xs font-semibold text-indigo-600 bg-indigo-50 rounded-full mb-4 tracking-wide">ARCHITECTURE</span>
                <h2 className="text-3xl md:text-5xl font-bold text-gray-900 mb-4">三层架构设计</h2>
                <p className="text-lg text-gray-500 max-w-2xl mx-auto">确保数据隐私与协作效率的完美平衡</p>
              </div>
            </RevealSection>

            <div className="grid lg:grid-cols-3 gap-8">
              {[
                { icon: Server, title: '协调服务端', subtitle: 'FastAPI + PostgreSQL + pgvector', color: 'blue', items: ['任务管理与发布', '语义匹配引擎', 'Flower训练协调', '差分隐私配置', '贡献度计算与结算', '通知与消息系统'] },
                { icon: Globe, title: '需求方 Web 前端', subtitle: 'React + TailwindCSS + AntDesign', color: 'purple', items: ['需求方工作台', '任务发布与配置', '训练实时监控', '收益分配可视化', '隐私预算仪表盘', '管理员后台'] },
                { icon: Database, title: '数据方桌面客户端', subtitle: 'Python + Flower + PyTorch', color: 'green', items: ['本地数据不出域', '任务浏览与参与', '本地模型训练', '多模型类型支持', 'CSV数据自动加载', '训练状态实时上报'] },
              ].map((arch, i) => (
                <RevealSection key={i} delay={i * 150}>
                  <div className={`relative bg-gradient-to-br ${
                    arch.color === 'blue' ? 'from-blue-50 to-indigo-50 border-blue-100' :
                    arch.color === 'purple' ? 'from-purple-50 to-pink-50 border-purple-100' :
                    'from-green-50 to-emerald-50 border-green-100'
                  } rounded-2xl p-8 border h-full`}>
                    <div className="absolute top-4 right-4 opacity-20">
                      <arch.icon className="h-10 w-10" />
                    </div>
                    <h3 className="text-xl font-bold text-gray-900 mb-1">{arch.title}</h3>
                    <p className="text-sm text-gray-500 mb-6">{arch.subtitle}</p>
                    <div className="space-y-3">
                      {arch.items.map((item, j) => (
                        <div key={j} className="flex items-center gap-2 text-sm text-gray-700">
                          <CheckCircle className={`h-4 w-4 shrink-0 ${
                            arch.color === 'blue' ? 'text-blue-500' : arch.color === 'purple' ? 'text-purple-500' : 'text-green-500'
                          }`} />
                          {item}
                        </div>
                      ))}
                    </div>
                  </div>
                </RevealSection>
              ))}
            </div>
          </div>
        </section>

        {/* ═══ Section 5: 使用流程 ═══ */}
        <section id="workflow" className="py-28 bg-white">
          <div className="max-w-6xl mx-auto px-6">
            <RevealSection>
              <div className="text-center mb-16">
                <span className="inline-block px-3 py-1 text-xs font-semibold text-green-600 bg-green-50 rounded-full mb-4 tracking-wide">WORKFLOW</span>
                <h2 className="text-3xl md:text-5xl font-bold text-gray-900 mb-4">简单四步开始协作</h2>
              </div>
            </RevealSection>

            <div className="grid md:grid-cols-2 gap-16 max-w-5xl mx-auto">
              <RevealSection>
                <div>
                  <h3 className="text-xl font-bold text-gray-900 mb-8 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                      <Users className="h-5 w-5 text-blue-600" />
                    </div>
                    需求方（数据买方）
                  </h3>
                  <div className="space-y-8 relative before:absolute before:left-[19px] before:top-10 before:bottom-4 before:w-px before:bg-blue-100">
                    {[
                      { step: '1', title: '发布任务', desc: '选择模型类型、配置隐私参数、设置奖励池' },
                      { step: '2', title: '智能匹配', desc: '系统自动匹配合适的数据提供方' },
                      { step: '3', title: '联邦训练', desc: '一键启动训练，实时查看进度与隐私消耗' },
                      { step: '4', title: '获取模型', desc: '训练完成后下载高精度联合模型，结算分配' },
                    ].map((s, i) => (
                      <div key={i} className="flex gap-5 relative">
                        <div className="shrink-0 w-10 h-10 rounded-full bg-gradient-to-r from-blue-500 to-blue-600 text-white text-sm font-bold flex items-center justify-center shadow-lg shadow-blue-200/40 z-10">
                          {s.step}
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-900 text-lg">{s.title}</h4>
                          <p className="text-sm text-gray-500 mt-1">{s.desc}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </RevealSection>

              <RevealSection delay={200}>
                <div>
                  <h3 className="text-xl font-bold text-gray-900 mb-8 flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                      <Database className="h-5 w-5 text-green-600" />
                    </div>
                    数据提供方
                  </h3>
                  <div className="space-y-8 relative before:absolute before:left-[19px] before:top-10 before:bottom-4 before:w-px before:bg-green-100">
                    {[
                      { step: '1', title: '下载客户端', desc: '安装桌面端应用，注册数据方账号' },
                      { step: '2', title: '浏览任务', desc: '查看推荐任务，选择匹配的协作机会' },
                      { step: '3', title: '本地训练', desc: '指定CSV数据路径，客户端自动训练' },
                      { step: '4', title: '获得收益', desc: '按贡献度获得对应的数据价值报酬' },
                    ].map((s, i) => (
                      <div key={i} className="flex gap-5 relative">
                        <div className="shrink-0 w-10 h-10 rounded-full bg-gradient-to-r from-green-500 to-green-600 text-white text-sm font-bold flex items-center justify-center shadow-lg shadow-green-200/40 z-10">
                          {s.step}
                        </div>
                        <div>
                          <h4 className="font-semibold text-gray-900 text-lg">{s.title}</h4>
                          <p className="text-sm text-gray-500 mt-1">{s.desc}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </RevealSection>
            </div>
          </div>
        </section>

        {/* ═══ Section 6: 底部 — 买方登录/注册 ═══ */}
        <section id="auth" className="relative py-28 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900" />
          <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)', backgroundSize: '40px 40px' }} />

          <div className="relative z-10 max-w-5xl mx-auto px-6">
            <div className="grid md:grid-cols-2 gap-16 items-center">
              {/* 左侧文案 */}
              <RevealSection>
                <div className="text-white">
                  <h2 className="text-3xl md:text-4xl font-bold mb-6">
                    开始安全的
                    <br />数据协作之旅
                  </h2>
                  <p className="text-blue-100/80 text-lg leading-relaxed mb-8">
                    作为数据需求方，您可以在平台上发布联邦学习任务，系统将自动为您匹配最合适的数据提供方。训练过程全程加密，数据不出本地。
                  </p>
                  <div className="space-y-4">
                    {[
                      '发布任务，智能匹配数据提供方',
                      '差分隐私保障训练安全',
                      '实时监控训练进度与隐私消耗',
                      '按贡献度自动分配收益',
                    ].map((t, i) => (
                      <div key={i} className="flex items-center gap-3 text-blue-100/90">
                        <CheckCircle className="h-5 w-5 text-green-400 shrink-0" />
                        <span>{t}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </RevealSection>

              {/* 右侧登录/注册表单 */}
              <RevealSection delay={200}>
                <div className="bg-white rounded-2xl shadow-2xl p-8">
                  {/* Tab切换 */}
                  <div className="flex mb-6 bg-gray-100 rounded-lg p-1">
                    <button
                      onClick={() => { setAuthMode('login'); setErrors({}); }}
                      className={`flex-1 py-2.5 text-sm font-medium rounded-md transition-all ${
                        authMode === 'login' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      登录
                    </button>
                    <button
                      onClick={() => { setAuthMode('register'); setErrors({}); }}
                      className={`flex-1 py-2.5 text-sm font-medium rounded-md transition-all ${
                        authMode === 'register' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      注册
                    </button>
                  </div>

                  <form onSubmit={authMode === 'login' ? handleLogin : handleRegister} className="space-y-4" autoComplete="off">
                    {/* 用户名 */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">用户名</label>
                      <div className="relative">
                        <UserOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                          name="username"
                          value={form.username}
                          onChange={handleChange}
                          placeholder="请输入用户名"
                          autoComplete="off"
                          className={`w-full pl-10 pr-4 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all ${errors.username ? 'border-red-300' : 'border-gray-200'}`}
                        />
                      </div>
                      {errors.username && <p className="mt-1 text-xs text-red-500">{errors.username}</p>}
                    </div>

                    {/* 邮箱（仅注册） */}
                    {authMode === 'register' && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
                        <div className="relative">
                          <MailOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                          <input
                            name="email"
                            type="email"
                            value={form.email}
                            onChange={handleChange}
                            placeholder="请输入邮箱"
                            className={`w-full pl-10 pr-4 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all ${errors.email ? 'border-red-300' : 'border-gray-200'}`}
                          />
                        </div>
                        {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email}</p>}
                      </div>
                    )}

                    {/* 密码（正式密码模式显示） */}
                    {!PASSWORDLESS_AUTH ? (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">密码</label>
                        <div className="relative">
                          <LockOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                          <input
                            name="password"
                            type={showPwd ? 'text' : 'password'}
                            value={form.password}
                            onChange={handleChange}
                            placeholder="请输入密码"
                            autoComplete="new-password"
                            className={`w-full pl-10 pr-10 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all ${errors.password ? 'border-red-300' : 'border-gray-200'}`}
                          />
                          <button type="button" onClick={() => setShowPwd(!showPwd)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                            {showPwd ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </button>
                        </div>
                        {errors.password && <p className="mt-1 text-xs text-red-500">{errors.password}</p>}
                      </div>
                    ) : (
                      <p className="text-xs text-gray-500">
                        当前为本地开发免密模式：输入 admin 可直接访问全部权限。
                      </p>
                    )}

                    {/* 确认密码（仅注册） */}
                    {!PASSWORDLESS_AUTH && authMode === 'register' && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">确认密码</label>
                        <div className="relative">
                          <LockOutlined className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                          <input
                            name="confirmPassword"
                            type="password"
                            value={form.confirmPassword}
                            onChange={handleChange}
                            placeholder="再次输入密码"
                            className={`w-full pl-10 pr-4 py-2.5 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all ${errors.confirmPassword ? 'border-red-300' : 'border-gray-200'}`}
                          />
                        </div>
                        {errors.confirmPassword && <p className="mt-1 text-xs text-red-500">{errors.confirmPassword}</p>}
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={loading}
                      className="w-full py-3 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg hover:shadow-lg hover:shadow-blue-200/50 transition-all duration-300 disabled:opacity-50"
                    >
                      {loading ? '处理中...' : authMode === 'login' ? '登录' : '注册'}
                    </button>
                  </form>
                </div>
              </RevealSection>
            </div>
          </div>
        </section>

        {/* ═══ Footer ═══ */}
        <footer className="bg-gray-900 text-gray-400 py-8 border-t border-gray-800">
          <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded bg-gradient-to-br from-blue-600 to-purple-600 text-white flex items-center justify-center text-[9px] font-bold">FL</div>
              <span className="text-sm">FedLearn Platform</span>
            </div>
            <p className="text-sm text-gray-500">基于联邦学习的隐私安全数据协作平台 &copy; {new Date().getFullYear()}</p>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default LandingPage;
