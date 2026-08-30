"""Endpoints HTTP agrupados por dominio.

main.py solo arma la aplicacion (CORS, licencia, estaticos) e incluye estos
routers. Antes todo vivia en un unico main.py de 2600 lineas donde convivian
la configuracion del servidor, el protocolo de sincronizacion, los CRUD, los
reportes y el parseo de Excel.
"""
