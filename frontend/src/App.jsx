import { lazy, Suspense } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { Loading } from './components/ui'
import { DatasetProvider } from './lib/dataset'
import Overview from './pages/Overview'

const Explorer = lazy(() => import('./pages/Explorer'))
const StartupDetail = lazy(() => import('./pages/StartupDetail'))
const Predict = lazy(() => import('./pages/Predict'))
const Upload = lazy(() => import('./pages/Upload'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Reports = lazy(() => import('./pages/Reports'))
const About = lazy(() => import('./pages/About'))
const NotFound = lazy(() => import('./pages/NotFound'))

export function AppRoutes() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Overview />} />
          <Route path="explorer" element={<Explorer />} />
          <Route path="startups/:id" element={<StartupDetail />} />
          <Route path="predict" element={<Predict />} />
          <Route path="upload" element={<Upload />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="reports" element={<Reports />} />
          <Route path="about" element={<About />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Suspense>
  )
}

export default function App() {
  return (
    <DatasetProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </DatasetProvider>
  )
}
