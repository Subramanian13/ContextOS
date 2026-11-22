import { Navigate, Route, Routes } from 'react-router-dom'
import { Shell } from './components/Shell'
import { Dashboard } from './pages/Dashboard'
import { ProjectPage } from './pages/ProjectPage'
import { ProposalsPage } from './pages/ProposalsPage'
import { ActivityPage } from './pages/ActivityPage'

export function App() {
  return <Routes><Route element={<Shell/>}><Route index element={<Dashboard/>}/><Route path="projects/:projectId" element={<ProjectPage/>}/><Route path="projects/:projectId/risks" element={<ProjectPage view="risks"/>}/><Route path="projects/:projectId/timeline" element={<ProjectPage view="timeline"/>}/><Route path="projects/:projectId/recovery" element={<ProjectPage view="recovery"/>}/><Route path="proposals" element={<ProposalsPage/>}/><Route path="activity" element={<ActivityPage/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Route></Routes>
}
