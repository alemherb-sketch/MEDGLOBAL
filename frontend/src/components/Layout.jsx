import { Link, Outlet, useLocation } from 'react-router-dom';
import { Home, Users, Settings, Pill, Stethoscope, Package, CalendarDays, UserRoundPlus } from 'lucide-react';

const Layout = () => {
  const location = useLocation();

  const navItems = [
    { path: '/', label: 'Dashboard', icon: <Home size={20} /> },
    { path: '/citas', label: 'Programación Citas', icon: <CalendarDays size={20} /> },
    { path: '/atenciones', label: 'Atenciones', icon: <Stethoscope size={20} /> },
    { path: '/medicamentos', label: 'Catálogo Medicamentos', icon: <Pill size={20} /> },
    { path: '/almacen', label: 'Almacén / Kardex', icon: <Package size={20} /> },
    { path: '/planilla', label: 'Planilla', icon: <Users size={20} /> },
    { path: '/personal-salud', label: 'Personal de Salud', icon: <UserRoundPlus size={20} /> },
    { path: '/sistemas', label: 'Sistemas Clínicos', icon: <Settings size={20} /> },
  ];

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand">MEDGLOBAL</div>
        <nav>
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-link ${location.pathname === item.path ? 'active' : ''}`}
            >
              <span style={{ marginRight: '12px', display: 'flex' }}>{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
