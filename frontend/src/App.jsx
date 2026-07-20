import { HashRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import RequireAuth from './components/RequireAuth';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Atenciones from './pages/Atenciones';
import Medicamentos from './pages/Medicamentos';
import Almacen from './pages/Almacen';
import Planilla from './pages/Planilla';
import Sistemas from './pages/Sistemas';
import PersonalSalud from './pages/PersonalSalud';
import Empresas from './pages/Empresas';
import DiagnosticosCie10 from './pages/DiagnosticosCie10';
import ConsumoMedicamentos from './pages/ConsumoMedicamentos';

function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
          <Route index element={<Dashboard />} />
          <Route path="atenciones" element={<Atenciones />} />
          <Route path="medicamentos" element={<Medicamentos />} />
          <Route path="almacen" element={<Almacen />} />
          <Route path="planilla" element={<Planilla />} />
          <Route path="empresas" element={<Empresas />} />
          <Route path="personal-salud" element={<PersonalSalud />} />
          <Route path="sistemas" element={<Sistemas />} />
          <Route path="diagnosticos-cie10" element={<DiagnosticosCie10 />} />
          <Route path="consumo-medicamentos" element={<ConsumoMedicamentos />} />
        </Route>
      </Routes>
    </HashRouter>
  );
}

export default App;
