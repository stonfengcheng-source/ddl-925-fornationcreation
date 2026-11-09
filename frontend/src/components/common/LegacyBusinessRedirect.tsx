import { Navigate, useLocation } from 'react-router-dom';

export default function LegacyBusinessRedirect({ oldPath, newPath }: { oldPath: string; newPath: string }) {
  const location = useLocation();
  return <Navigate replace to={`${location.pathname.replace(oldPath, newPath)}${location.search}${location.hash}`} />;
}
