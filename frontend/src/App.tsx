import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import StudyList from "./pages/StudyList";
import StudyDetail from "./pages/StudyDetail";
import KeyManagement from "./pages/KeyManagement";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<StudyList />} />
        <Route path="/studies/:id" element={<StudyDetail />} />
        <Route path="/keys" element={<KeyManagement />} />
      </Route>
    </Routes>
  );
}
