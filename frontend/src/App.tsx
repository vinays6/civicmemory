import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import IngestionHub from './pages/IngestionHub';
import NetworkDashboard from './pages/NetworkDashboard';
import EntityExplorer from './pages/EntityExplorer';
import Methodology from './pages/Methodology';
import PoliticianProfile from './pages/PoliticianProfile';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout><IngestionHub /></Layout>} path="/" />
        <Route element={<Layout><NetworkDashboard /></Layout>} path="/network" />
        <Route element={<Layout><EntityExplorer /></Layout>} path="/entities" />
        <Route element={<Layout><Methodology /></Layout>} path="/methodology" />
        <Route element={<Layout><PoliticianProfile /></Layout>} path="/politician/:id" />
      </Routes>
    </BrowserRouter>
  );
}
