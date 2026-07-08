import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Atenciones from './pages/Atenciones';
import Medicamentos from './pages/Medicamentos';
import Almacen from './pages/Almacen';
import Planilla from './pages/Planilla';
import Sistemas from './pages/Sistemas';
import PersonalSalud from './pages/PersonalSalud';
import Empresas from './pages/Empresas';
import DiagnosticosCie10 from './pages/DiagnosticosCie10';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="atenciones" element={<Atenciones />} />
          <Route path="medicamentos" element={<Medicamentos />} />
          <Route path="almacen" element={<Almacen />} />
          <Route path="planilla" element={<Planilla />} />
          <Route path="empresas" element={<Empresas />} />
          <Route path="personal-salud" element={<PersonalSalud />} />
          <Route path="sistemas" element={<Sistemas />} />
          <Route path="diagnosticos-cie10" element={<DiagnosticosCie10 />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
