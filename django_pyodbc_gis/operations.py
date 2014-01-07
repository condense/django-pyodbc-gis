from django.contrib.gis.db.backends.base import BaseSpatialOperations
from django.contrib.gis.db.backends.util import SpatialFunction
from django.contrib.gis.measure import Distance
from sql_server.pyodbc.operations import DatabaseOperations


class MSSqlMethod(SpatialFunction):
    """SQL Server (non-static) spatial functions are treated as methods,
    for eg g.STContains(p)"""

    sql_template = '[%(geo_col)s].%(function)s(%(geometry)s)'

    def __init__(self, function, **kwargs):
        super(MSSqlMethod, self).__init__(function, **kwargs)


class MSSqlOperations(DatabaseOperations, BaseSpatialOperations):

    name = 'SQL Server'
    select = '%s.STAsText()'
    from_wkb = 'STGeomFromWKB'
    from_text = 'STGeomFromText'

    # We do have a geography type as well, but let's get geometry
    # working first:
    geometry = True

    # 'bbcontains'
    # 'bboverlaps'
    # 'contained'
    # 'contains'
    # 'contains_properly'
    # 'coveredby'
    # 'covers'
    # 'crosses'
    # 'disjoint'
    # 'distance_gt'
    # 'distance_gte'
    # 'distance_lt'
    # 'distance_lte'
    # 'dwithin'
    # 'equals'
    # 'exact'
    # 'intersects'
    # 'overlaps'
    # 'relate'
    # 'same_as'
    # 'touches'
    # 'within'
    # 'left'
    # 'right'
    # 'overlaps_left'
    # 'overlaps_right'
    # 'overlaps_above'
    # 'overlaps_below'
    # 'strictly_above'
    # 'strictly_below'

    geometry_functions = {
        'contains': MSSqlMethod('STContains'),
        'crosses': MSSqlMethod('STCrosses'),
        'disjoint': MSSqlMethod('STDisjoint'),
        'equals': MSSqlMethod('STEquals'),  # can we also implement exact, same_as like this?
        'intersects': MSSqlMethod('STIntersects'),
        'overlaps': MSSqlMethod('STOverlaps'),
        'touches': MSSqlMethod('STTouches'),
        'within': MSSqlMethod('STWithin'),
    }

    def spatial_lookup_sql(self, lvalue, lookup_type, value, field):
        raise NotImplementedError

    # GeometryField operations
    def geo_db_type(self, f):
        return f.geom_type

    def get_distance(self, f, value, lookup_type):
        """
        Returns the distance parameters for the given geometry field,
        lookup value, and lookup type.  This is based on the Spatialite
        backend, since we don't currently support geography operations.
        """
        if not value:
            return []
        value = value[0]
        if isinstance(value, Distance):
            if f.geodetic(self.connection):
                raise ValueError('The SQL Server backend does not support '
                                 'distance queries on geometry fields with '
                                 'a geodetic coordinate system. Distance '
                                 'objects; use a numeric value of your '
                                 'distance in degrees instead.')
            else:
                dist_param = getattr(value, Distance.unit_attname(f.units_name(self.connection)))
        else:
            dist_param = value
        return [dist_param]

    def get_geom_placeholder(self, f, value):
        """
        Returns the placeholder for the given geometry field with the given
        value.  Depending on the spatial backend, the placeholder may contain a
        stored procedure call to the transformation function of the spatial
        backend.
        """
        raise NotImplementedError

    # Routines for getting the OGC-compliant models.
    def geometry_columns(self):
        raise NotImplementedError

    def spatial_ref_sys(self):
        raise NotImplementedError
