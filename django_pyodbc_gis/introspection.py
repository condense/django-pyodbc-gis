from django.contrib.gis.gdal import OGRGeomType

from sql_server.pyodbc.introspection import DatabaseIntrospection
import re


class GeoIntrospectionError(Exception):
    pass


class MSSqlIntrospection(DatabaseIntrospection):

    def get_geometry_type(self, table_name, geo_col):
        """
        The geometry type used by SQL Server doesn't contain any
        specific type, SRID,or dimension information; that is
        associated with instances.  This makes introspection hacky and
        error prone, but presumably that also applies to the data
        integrity.
        """
        cursor = self.connection.cursor()
        try:
            field_type, field_params = None, {}
            # Look for a sample piece of data and assume that it's
            # representative.  If we can't find anything, we'll have
            # to examine the constraints:
            try:
                cursor.excute("SELECT TOP 1 [%(geo_col)].STGeometryType(), " +
                              "[%(geo_col)].STDimension(), " +
                              "[%(geo_col)].STSrid " +
                              "FROM [%(table_name)] " +
                              "WHERE [%(geo_col)] IS NOT NULL" % locals())

                row = cursor.fetchone()

                if not rows:
                    raise GeoIntrospectionError

                field_type = OGRGeomType(row[0]).django

                srid, dim = row[1:]
                if srid != 4326:
                    field_params['srid'] = srid
                if dim != 2:
                    field_params['dim'] = dim

            except GeoIntrospectionError:
                # The table is empty, so we'll have to guess based on
                # parsing the constraint information.  Unfortunately,
                # this will only give us the type, but not dimension
                # or SRID (and nothing reliably)
                cursor.execute(
                    "SELECT [CHECK_CLAUSE]"
                    "FROM [INFORMATION_SCHEMA].[CHECK_CONSTRAINTS] cc"
                    "JOIN [INFORMATION_SCHEMA].[CONSTRAINT_COLUMN_USAGE] ccu"
                    "ON ccu.[CONSTRAINT_NAME] = cc.[CONSTRAINT_NAME]"
                    "WHERE ccu.[CONSTRAINT_CATALOG] = '%s'"
                    "AND [COLUMN_NAME] = '%s'" % (table_name, geo_col)
                )

                rows = cursor.fetchall()
                if rows:

                    # Sample to parse:
                    # ([geom].[STGeometryType]()='Point')
                    type_re = re.compile(r"\[STGeometryType\]\(\)='(\w+)'")
                    for row in rows:
                        constraint = row[0]
                        m = type_re.search(constraint)
                        if m:
                            field_type = OGRGeomType(m.group(1)).django
                            break

        finally:
            cursor.close()

        return field_type, field_params
