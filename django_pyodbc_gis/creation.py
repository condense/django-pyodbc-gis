from sql_server.pyodbc.creation import DatabaseCreation


class MSSqlCreation(DatabaseCreation):
    """
    This class encapsulates all backend-specific differences that pertain to
    database *creation*, such as the column types to use for particular Django
    Fields, the SQL used to create and destroy tables, and the creation and
    destruction of test databases.
    """

    def sql_indexes_for_field(self, model, f, style):
        from django.contrib.gis.db.models.fields import GeometryField
        output = super(MSSqlCreation, self).sql_indexes_for_field(model, f, style)

        if isinstance(f, GeometryField):
            qn = self.connection.ops.quote_name
            db_table = model._meta.db_table
            constraint_name = 'chk_%s_%s_%s' % \
                              (db_table, f.column, f.geom_type)

            # Geometry-type constraint:
            output.append(style.SQL_KEYWORD('ALTER TABLE ') +
                          style.SQL_TABLE(qn(db_table)) +
                          style.SQL_KEYWORD('ADD CONSTRAINT ') +
                          style.SQL_TABLE(qn(constraint_name)) +
                          style.SQL_KEYWORD(' CHECK ( ') +
                          style.SQL_FIELD(qn(f.column)) +
                          '.STGeometryType() = \'' +
                          style.SQL_KEYWORD(f.geom_type) + '\' )')

            # Spatial index; see:
            # http://technet.microsoft.com/en-us/library/bb934196.aspx
            if f.spatial_index:
                idx_name = '%s_%s_id' % (db_table, f.column)
                extent = str(f._extent)
                output.append(style.SQL_KEYWORD('CREATE SPATIAL INDEX ') +
                              style.SQL_TABLE(qn(idx_name)) +
                              style.SQL_KEYWORD(' ON ') +
                              style.SQL_TABLE(qn(db_table)) + '(' +
                              style.SQL_FIELD(qn(f.column)) + ') ' +
                              style.SQL_KEYWORD('USING GEOMETRY_AUTO_GRID ') +
                              style.SQL_KEYWORD('WITH ') + '(' +
                              style.SQL_KEYWORD('BOUNDING_BOX') + ' = ' +
                              extent + ' )')

        return output
