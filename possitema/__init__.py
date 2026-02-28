"""Inicialización del paquete possitema.

Instala PyMySQL como reemplazo de MySQLdb si está disponible, para
permitir que Django use el motor MySQL sobre PyMySQL.
"""
try:
	import pymysql
	pymysql.install_as_MySQLdb()
except Exception:
	# Si PyMySQL no está disponible, no interrumpir la carga; Django
	# fallará al conectar si no hay un conector instalado.
	pass
