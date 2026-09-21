import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout, Row, Col, Spin, Button, Breadcrumb } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';

// Components
import OverallScoreCard from './components/OverallScoreCard';
import LayerRadarChart from './components/LayerRadarChart';
import ScenarioTagCloud from './components/ScenarioTagCloud';
import DiagnosticDetails from './components/DiagnosticDetails';
import RecommendationPanel from './components/RecommendationPanel';

// Mock Data
import { mockQualityReport } from '../../../mocks/qualityReportMock';
import { QualityReport as QualityReportType } from '../../../types/quality';

const { Content } = Layout;

const QualityReport: React.FC = () => {
  const { dataId } = useParams<{ dataId: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<QualityReportType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 模拟 API 请求
    setTimeout(() => {
      setReport(mockQualityReport);
      setLoading(false);
    }, 800);
  }, [dataId]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen bg-gray-50">
        <Spin size="large" tip="正在生成质量报告..." />
      </div>
    );
  }

  if (!report) return <div>报告不存在</div>;

  return (
    <Content className="p-6 bg-gray-50 min-h-screen">
      {/* 顶部导航区 */}
      <div className="mb-6">
        <Breadcrumb
          items={[
            { title: '任务广场' },
            { title: '数据详情' },
            { title: '质量报告' },
          ]}
          className="mb-4"
        />
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate(-1)}
              type="text"
            />
            <div>
              <h1 className="text-2xl font-bold m-0">数据质量评估报告</h1>
              <p className="text-gray-500 m-0 text-sm">ID: {dataId} | 生成时间: {new Date(report.generatedAt).toLocaleDateString()}</p>
            </div>
          </div>
          <Button type="primary">导出报告</Button>
        </div>
      </div>

      {/* 核心指标区 */}
      <Row gutter={[16, 16]} className="mb-4">
        <Col xs={24} md={8}>
          <OverallScoreCard score={report.overallScore} rating={report.rating} />
        </Col>
        <Col xs={24} md={16}>
          <LayerRadarChart layerScores={report.layerScores} />
        </Col>
      </Row>

      {/* 场景标签 */}
      <ScenarioTagCloud
        suitableScenarios={report.suitableScenarios}
        unsuitableScenarios={report.unsuitableScenarios}
      />

      {/* 详细诊断 */}
      <DiagnosticDetails details={report.diagnosticDetails} />

      {/* 优化建议 */}
      <RecommendationPanel recommendations={report.recommendations} />
    </Content>
  );
};

export default QualityReport;
