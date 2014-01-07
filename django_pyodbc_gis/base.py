from sql_server.pyodbc.base import *
from sql_server.pyodbc.base import DatabaseWrapper as MSSqlDatabaseWrapper
from django_pyodbc_gis.creation import MSSqlCreation
from django_pyodbc_gis.introspection import MSSqlIntrospection
from django_pyodbc_gis.operations import MSSqlOperations


class DatabaseWrapper(MSSqlDatabaseWrapper):

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self.creation = MSSqlCreation(self)
        self.ops = MSSqlOperations(self)
        self.introspection = MSSqlIntrospection(self)
