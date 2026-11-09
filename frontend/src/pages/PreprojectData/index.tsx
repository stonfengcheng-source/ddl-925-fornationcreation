import { useParams } from 'react-router-dom';
import { PreprojectLayout } from './layout/PreprojectLayout';
import { SourcesPage } from './pages/SourcesPage';
import { PipelinePage } from './pages/PipelinePage';
import { TasksPage } from './pages/TasksPage';
import { QualityPage } from './pages/QualityPage';
import { ReviewsPage } from './pages/ReviewsPage';
import { VersionsPage } from './pages/VersionsPage';

const pages: Record<string, JSX.Element> = { sources: <SourcesPage />, pipelines: <PipelinePage />, tasks: <TasksPage />, quality: <QualityPage />, reviews: <ReviewsPage />, versions: <VersionsPage /> };
export default function PreprojectDataPage() {
  const { section = 'sources' } = useParams();
  return <PreprojectLayout>{pages[section] || <p>页面不存在，请选择工作台功能。</p>}</PreprojectLayout>;
}
