from decimal import Decimal

from django.contrib.gis.db.backends.base import BaseSpatialOperations
from django.contrib.gis.db.backends.util import SpatialFunction
from django.contrib.gis.geometry.backend import Geometry
from django.contrib.gis.measure import Distance
from django.utils import six
from sql_server.pyodbc.operations import DatabaseOperations


class MSSqlBoolMethod(SpatialFunction):
    """SQL Server (non-static) spatial functions are treated as methods,
    for eg g.STContains(p)"""

    sql_template = '%(geo_col)s.%(function)s(%(geometry)s) = 1'

    def __init__(self, function, **kwargs):
        super(MSSqlBoolMethod, self).__init__(function, **kwargs)


class MSSqlDistanceFunc(SpatialFunction):
    """Implements distance comparison lookups, eg distance_lte"""

    sql_template = ('%(geo_col)s.%(function)s(%(geometry)s) '
                    '%(operator)s %(result)s')

    def __init__(self, op):
        super(MSSqlDistanceFunc, self).__init__('STDistance',
                                                operator=op,
                                                result='%s')


class MSSqlBBBoolMethod(MSSqlBoolMethod):
    """SQL Server has no native bounding-box methods, but we can emulate
    them with a slightly more complicated expression.  The call will
    be translated into something like
    col.STEnvelope().STOverlaps(geom.STEnvelope())
    where STEnvelope() first simplifies the geometries to their
    bounding rectangles."""

    sql_template = '%(geo_col)s.STEnvelope().%(function)s(%(geometry)s.STEnvelope()) = 1'

    def __init__(self, function, **kwargs):
        super(MSSqlBoolMethod, self).__init__(function, **kwargs)


class MSSqlAdapter(str):
    """This adapter works around an apparent bug in the pyodbc driver
    itself.  We only require the wkt adapter, but if we use
    django.contrib.gis.db.backends.adapter.WKTAdapter then
    cursor.execute() fails because it doesn't call str() on unrecognised
    types.  So we make sure that our adaper *is* a string."""

    def __new__(cls, geom):
        geostr = str.__new__(cls, geom.wkt)
        geostr.srid = geom.srid
        return geostr

    def __eq__(self, other):
        if not isinstance(other, MSSqlAdapter):
            return False
        return super(MSSqlAdapter, self).__eq__(other) and \
            self.srid == other.srid

    def prepare_database_save(self, unused):
        return self


# Valid distance types and substitutions
dtypes = (Decimal, Distance, float) + six.integer_types


class MSSqlOperations(DatabaseOperations, BaseSpatialOperations):

    name = 'SQL Server'
    select = '%s.STAsText()'

    Adapter = MSSqlAdapter
    Adaptor = Adapter  # Backwards-compatibility alias.

    compiler_module = 'django_pyodbc_gis.compiler'

    geometry = True
    geography = True

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
        'bbcontains': MSSqlBBBoolMethod('STContains'),
        'bboverlaps': MSSqlBBBoolMethod('STOverlaps'),
        'contained': MSSqlBBBoolMethod('STWithin'),
        'contains': MSSqlBoolMethod('STContains'),
        'crosses': MSSqlBoolMethod('STCrosses'),
        'disjoint': MSSqlBoolMethod('STDisjoint'),
        'equals': MSSqlBoolMethod('STEquals'),  # can we also implement exact, same_as like this?
        'intersects': MSSqlBoolMethod('STIntersects'),
        'overlaps': MSSqlBoolMethod('STOverlaps'),
        'touches': MSSqlBoolMethod('STTouches'),
        'within': MSSqlBoolMethod('STWithin'),
    }

    distance_functions = {
        'distance_gt': (MSSqlDistanceFunc('>'), dtypes),
        'distance_gte': (MSSqlDistanceFunc('>='), dtypes),
        'distance_lt': (MSSqlDistanceFunc('<'), dtypes),
        'distance_lte': (MSSqlDistanceFunc('<='), dtypes),
    }
    geometry_functions.update(distance_functions)

    geography_functions = {
        'contains': MSSqlBoolMethod('STContains'),
        'disjoint': MSSqlBoolMethod('STDisjoint'),
        'equals': MSSqlBoolMethod('STEquals'),
        'intersects': MSSqlBoolMethod('STIntersects'),
        'overlaps': MSSqlBoolMethod('STOverlaps'),
        'within': MSSqlBoolMethod('STWithin'),
    }
    geography_functions.update(distance_functions)

    gis_terms = set(geometry_functions) | set(['isnull'])

    collect = 'CollectionAggregate'
    extent = 'EnvelopeAggregate'
    unionagg = 'UnionAggregate'

    valid_aggregates = dict([(k, None) for k in
                             ('Collect', 'Extent', 'Union')])

    def spatial_lookup_sql(self, lvalue, lookup_type, value, field, qn):
        alias, col, db_type = lvalue

        geo_col = '%s.%s' % (qn(alias), qn(col))

        if field.geography:
            if lookup_type not in self.geography_functions:
                raise TypeError("Got invalid lookup_type for geography: %s" %
                                lookup_type)
        else:
            if lookup_type not in self.geometry_functions:
                raise TypeError("Got invalid lookup_type for geometry: %s" %
                                lookup_type)

        if lookup_type == 'isnull':
            return "%s IS %sNULL" % (geo_col, ('' if value else 'NOT ')), []

        else:
            if field.geography:
                op = self.geography_functions[lookup_type]
            else:
                op = self.geometry_functions[lookup_type]

            # if lookup_type is a tuple then we expect the value to be
            # a tuple as well:
            if isinstance(op, tuple):
                dist_op, arg_type = op

                # Ensuring that a tuple _value_ was passed in from the user
                if not isinstance(value, tuple):
                    raise ValueError('Tuple required for `%s` lookup type.' %
                                     lookup_type)
                if len(value) != 2:
                    raise ValueError('2-element tuple required for %s lookup type.' %
                                     lookup_type)

                # Ensuring the argument type matches what we expect.
                if not isinstance(value[1], arg_type):
                    raise ValueError('Argument type should be %s, got %s instead.' %
                                     (arg_type, type(value[1])))

                geom = value[0]
                return dist_op.as_sql(geo_col, self.get_geom_placeholder(field, geom))

            return op.as_sql(geo_col, self.get_geom_placeholder(field, value))

    def check_aggregate_support(self, aggregate):
        """
        Checks if the given aggregate name is supported (that is, if it's
        in `self.valid_aggregates`).
        """
        agg_name = aggregate.__class__.__name__
        return agg_name in self.valid_aggregates

    def spatial_aggregate_sql(self, agg):
        """
        Returns the spatial aggregate SQL template and function for the
        given Aggregate instance.
        """
        agg_name = agg.__class__.__name__
        if not self.check_aggregate_support(agg):
            raise NotImplementedError('%s spatial aggregate is not implmented '
                                      'for this backend.' % agg_name)
        agg_name = agg_name.lower()
        if agg_name == 'union':
            agg_name += 'agg'
        # We need to namespace the function depending on whether it's
        # for a geography or geometry (which requires digging into the
        # Aggregate), but the function name is the same for both:
        ns = 'geography' if agg.source.geography else 'geometry'
        sql_template = ns + '::%(function)s(%(field)s).ToString()'
        sql_function = getattr(self, agg_name)
        return sql_template, sql_function

    def convert_extent(self, poly):
        """
        Returns a 4-tuple extent for the `Extent` aggregate by converting
        the bounding box text returned by SQL Server (`poly` argument), for
        example: "POLYGON ((0 0, 2 0, 2 3, 0 3, 0 0))".
        """
        crnrs = poly[10:-2].split(',')
        xmin, ymin = map(float, crnrs[0].strip().split(' '))
        xmax, ymax = map(float, crnrs[2].strip().split(' '))
        return xmin, ymin, xmax, ymax

    def convert_geom(self, hex, geo_field):
        """
        Converts the geometry returned from aggregate queries.
        """
        if hex:
            return Geometry(hex)
        else:
            return None

    # GeometryField operations
    def geo_db_type(self, f):
        # We only have the one geometry type (especially since we
        # don't currently support geography):
        return 'geometry'

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
        Because SQL Server does not support spatial transformations,
        there is no need to modify the placeholder based on the
        contents of the given value.  We do need to specify the SRID
        however, since this argument is required.
        """
        if hasattr(value, 'expression'):
            placeholder = self.get_expression_column(value)
        else:
            ns = 'geography' if f.geography else 'geometry'
            placeholder = '%s::STGeomFromText(%%s,%s)' % (ns, f.srid)
        return placeholder

    # Routines for getting the OGC-compliant models --- SQL Server
    # does not have OGC-compliant tables
    def geometry_columns(self):
        raise NotImplementedError

    def spatial_ref_sys(self):
        raise NotImplementedError
