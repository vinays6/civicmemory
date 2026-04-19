import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import MembersIndex from './pages/MembersIndex';
import MemberProfile from './pages/MemberProfile';
import VotingNetwork from './pages/VotingNetwork';

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<MembersIndex />} />
          <Route path="/network" element={<VotingNetwork />} />
          <Route path="/members/:name" element={<MemberProfile />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
