import { HashRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import RequireAuth from './components/RequireAuth';
import RequireLicense from './components/RequireLicense';
import ActivarLicencia from './pages/ActivarLicencia';
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
import Botiquin from './pages/Botiquin';
import InspeccionBotiquin from './pages/InspeccionBotiquin';

// La licencia se comprueba sobre /login y no sobre cada pantalla: para entrar
// a cualquier otra ruta hay que estar autenticado, y para autenticarse hay que
// pasar por aca.
//
// Sin este cableado la version de escritorio queda inutilizable en una PC sin
// licencia: el backend responde 403 a /auth/login y el usuario ve "Usuario o
// contraseña incorrectos" -- un mensaje que no tiene nada que ver -- sin
// ninguna forma de llegar a la pantalla de activacion, que existe pero no
// estaba enrutada. En la web del VPS /licencias/estado responde
// requerido=false y RequireLicense deja pasar sin hacer nada.
function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/activar-licencia" element={<ActivarLicencia />} />
        <Route path="/login" element={<RequireLicense><Login /></RequireLicense>} />
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
          <Route path="botiquin" element={<Botiquin />} />
          <Route path="inspeccion" element={<InspeccionBotiquin />} />
        </Route>
      </Routes>
    </HashRouter>
  );
}

export default App;
