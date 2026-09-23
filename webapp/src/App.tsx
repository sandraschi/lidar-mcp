import { HashRouter, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import Dashboard from "./pages/Dashboard";
import Console from "./pages/Console";
import Scope from "./pages/Scope";
import Mapper from "./pages/Mapper";
import DiffLab from "./pages/DiffLab";
import Ptz3D from "./pages/Ptz3D";
import Library from "./pages/Library";
import Raspbots from "./pages/Raspbots";
import Tools from "./pages/Tools";
import Skills from "./pages/Skills";
import Apps from "./pages/Apps";
import Chat from "./pages/Chat";
import ApiDocs from "./pages/ApiDocs";
import Settings from "./pages/Settings";
import Help from "./pages/Help";
import Logs from "./pages/Logs";

export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="console" element={<Console />} />
          <Route path="scope" element={<Scope />} />
          <Route path="mapper" element={<Mapper />} />
          <Route path="diff" element={<DiffLab />} />
          <Route path="ptz3d" element={<Ptz3D />} />
          <Route path="library" element={<Library />} />
          <Route path="raspbots" element={<Raspbots />} />
          <Route path="tools" element={<Tools />} />
          <Route path="skills" element={<Skills />} />
          <Route path="apps" element={<Apps />} />
          <Route path="chat" element={<Chat />} />
          <Route path="api-docs" element={<ApiDocs />} />
          <Route path="settings" element={<Settings />} />
          <Route path="help" element={<Help />} />
          <Route path="logs" element={<Logs />} />
        </Route>
      </Routes>
    </HashRouter>
  );
}
