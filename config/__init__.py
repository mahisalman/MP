"""
Project configuration package initialization.

Registers PyMySQL as the MySQL database driver if mysqlclient is not present.
This ensures zero-friction cross-platform MySQL support across Windows and Linux.
"""

try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass
