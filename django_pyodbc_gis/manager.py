from django.db import connections
from django.db.models.query import QuerySet, ValuesQuerySet, ValuesListQuerySet

from django.contrib.gis import memoryview
from django.contrib.gis.db.models import aggregates
from django.contrib.gis.db.models.fields import get_srid_info, PointField, LineStringField
from django.contrib.gis.db.models.sql import AreaField, DistanceField, GeomField, GeoQuery
from django.contrib.gis.geometry.backend import Geometry
from django.contrib.gis.measure import Area, Distance

from django.utils import six


from django.contrib.gis.db.models import GeoManager
from django.contrib.gis.db.models.query import GeoQuerySet

# This code patches the GeoQuerySet as provided by Django 1.6.1
#
# MSSQL requires syntax unsupported by the current core libraries
# and this code adds features to facilitate support.
#
# The specific problems we ran into were:
#
# - to support queryset.distance() we need to construct an SQL query
#   with the format "SELECT pointa.STDistance(pointb)" but the code
#   presumes that the format will be "STDistance(pointa, pointb)"


class MSSqlGeoQuerySet(GeoQuerySet):

    def _distance_attribute(self, func, geom=None, tolerance=0.05, spheroid=False, **kwargs):
        """
        DRY routine for GeoQuerySet distance attribute routines.
        """

        print "_distance_attribute", func, geom, tolerance, spheroid, kwargs

        # Setting up the distance procedure arguments.
        procedure_args, geo_field = self._spatial_setup(func, field_name=kwargs.get('field_name', None))

        # If geodetic defaulting distance attribute to meters (Oracle and
        # PostGIS spherical distances return meters).  Otherwise, use the
        # units of the geometry field.
        connection = connections[self.db]
        geodetic = geo_field.geodetic(connection)
        geography = geo_field.geography

        #############################################################################
        # NOTE: Moved up to get basic MSSql going.
        # Getting the spatial backend operations.
        backend = connection.ops
        #############################################################################

        #############################################################################
        # TODO: Hacked to get basic MSSql going.  Needs investigating.
        # if geodetic:
        if geodetic or backend.mssql:
        #############################################################################
            dist_att = 'm'
        else:
            dist_att = Distance.unit_attname(geo_field.units_name(connection))

        # Shortcut booleans for what distance function we're using and
        # whether the geometry field is 3D.
        distance = func == 'distance'
        length = func == 'length'
        perimeter = func == 'perimeter'
        if not (distance or length or perimeter):
            raise ValueError('Unknown distance function: %s' % func)
        geom_3d = geo_field.dim == 3

        #############################################################################
        # NOTE: Added for MSSql
        # Flag to request method format (e.g. col.fun(args...) ) insteand of
        # function call format (e.g. fun(col, args...)).  Important for MSSql.
        method_call = False
        #############################################################################

        # The field's get_db_prep_lookup() is used to get any
        # extra distance parameters.  Here we set up the
        # parameters that will be passed in to field's function.
        lookup_params = [geom or 'POINT (0 0)', 0]

        # If the spheroid calculation is desired, either by the `spheroid`
        # keyword or when calculating the length of geodetic field, make
        # sure the 'spheroid' distance setting string is passed in so we
        # get the correct spatial stored procedure.
        if spheroid or (backend.postgis and geodetic and
                        (not geography) and length):
            lookup_params.append('spheroid')
        lookup_params = geo_field.get_prep_value(lookup_params)
        params = geo_field.get_db_prep_lookup('distance_lte', lookup_params, connection=connection)

        # The `geom_args` flag is set to true if a geometry parameter was
        # passed in.
        geom_args = bool(geom)


        if backend.oracle:
            if distance:
                procedure_fmt = '%(geo_col)s,%(geom)s,%(tolerance)s'
            elif length or perimeter:
                procedure_fmt = '%(geo_col)s,%(tolerance)s'
            procedure_args['tolerance'] = tolerance
        else:
            # Getting whether this field is in units of degrees since the field may have
            # been transformed via the `transform` GeoQuerySet method.
            if self.query.transformed_srid:
                u, unit_name, s = get_srid_info(self.query.transformed_srid, connection)
                geodetic = unit_name in geo_field.geodetic_units

            if backend.spatialite and geodetic:
                raise ValueError('SQLite does not support linear distance calculations on geodetic coordinate systems.')

            if distance:
                if self.query.transformed_srid:
                    # Setting the `geom_args` flag to false because we want to handle
                    # transformation SQL here, rather than the way done by default
                    # (which will transform to the original SRID of the field rather
                    #  than to what was transformed to).
                    geom_args = False
                    procedure_fmt = '%s(%%(geo_col)s, %s)' % (backend.transform, self.query.transformed_srid)
                    if geom.srid is None or geom.srid == self.query.transformed_srid:
                        # If the geom parameter srid is None, it is assumed the coordinates
                        # are in the transformed units.  A placeholder is used for the
                        # geometry parameter.  `GeomFromText` constructor is also needed
                        # to wrap geom placeholder for SpatiaLite.
                        if backend.spatialite:
                            procedure_fmt += ', %s(%%%%s, %s)' % (backend.from_text, self.query.transformed_srid)
                        else:
                            procedure_fmt += ', %%s'
                    else:
                        # We need to transform the geom to the srid specified in `transform()`,
                        # so wrapping the geometry placeholder in transformation SQL.
                        # SpatiaLite also needs geometry placeholder wrapped in `GeomFromText`
                        # constructor.
                        if backend.spatialite:
                            procedure_fmt += ', %s(%s(%%%%s, %s), %s)' % (backend.transform, backend.from_text,
                                                                          geom.srid, self.query.transformed_srid)
                        else:
                            procedure_fmt += ', %s(%%%%s, %s)' % (backend.transform, self.query.transformed_srid)
                else:
                    # `transform()` was not used on this GeoQuerySet.
                    #############################################################################
                    # NOTE: Added flag to support mssql distance call format
                    if backend.mssql:
                        procedure_fmt = '%(geom)s'
                        method_call = True
                    else:
                        procedure_fmt = '%(geo_col)s,%(geom)s'
                    #############################################################################

                if not geography and geodetic:
                    # Spherical distance calculation is needed (because the geographic
                    # field is geodetic). However, the PostGIS ST_distance_sphere/spheroid()
                    # procedures may only do queries from point columns to point geometries
                    # some error checking is required.
                    if not backend.geography:
                        if not isinstance(geo_field, PointField):
                            raise ValueError('Spherical distance calculation only supported on PointFields.')
                        if not str(Geometry(memoryview(params[0].ewkb)).geom_type) == 'Point':
                            raise ValueError('Spherical distance calculation only supported with Point Geometry parameters')
                    # The `function` procedure argument needs to be set differently for
                    # geodetic distance calculations.
                    if spheroid:
                        # Call to distance_spheroid() requires spheroid param as well.
                        procedure_fmt += ",'%(spheroid)s'"
                        procedure_args.update({'function': backend.distance_spheroid, 'spheroid': params[1]})
                    else:
                        procedure_args.update({'function': backend.distance_sphere})
            elif length or perimeter:
                procedure_fmt = '%(geo_col)s'
                if not geography and geodetic and length:
                    # There's no `length_sphere`, and `length_spheroid` also
                    # works on 3D geometries.
                    procedure_fmt += ",'%(spheroid)s'"
                    procedure_args.update({'function': backend.length_spheroid, 'spheroid': params[1]})
                elif geom_3d and backend.postgis:
                    # Use 3D variants of perimeter and length routines on PostGIS.
                    if perimeter:
                        procedure_args.update({'function': backend.perimeter3d})
                    elif length:
                        procedure_args.update({'function': backend.length3d})

        # Setting up the settings for `_spatial_attribute`.
        s = {'select_field': DistanceField(dist_att),
             'setup': False,
             'geo_field': geo_field,
             'procedure_args': procedure_args,
             'procedure_fmt': procedure_fmt,
             ########################################################################
             # NOTE: Added for MSSql
             'method_call': method_call,
             ########################################################################
             }
        if geom_args:
            s['geom_args'] = ('geom',)
            s['procedure_args']['geom'] = geom
        elif geom:
            # The geometry is passed in as a parameter because we handled
            # transformation conditions in this routine.
            s['select_params'] = [backend.Adapter(geom)]

        return self._spatial_attribute(func, s, **kwargs)


    def _spatial_attribute(self, att, settings, field_name=None, model_att=None):
        """
        DRY routine for calling a spatial stored procedure on a geometry column
        and attaching its output as an attribute of the model.

        Arguments:
         att:
          The name of the spatial attribute that holds the spatial
          SQL function to call.

         settings:
          Dictonary of internal settings to customize for the spatial procedure.

        Public Keyword Arguments:

         field_name:
          The name of the geographic field to call the spatial
          function on.  May also be a lookup to a geometry field
          as part of a foreign key relation.

         model_att:
          The name of the model attribute to attach the output of
          the spatial function to.
        """
        # Default settings.
        settings.setdefault('desc', None)
        settings.setdefault('geom_args', ())
        settings.setdefault('geom_field', None)
        settings.setdefault('procedure_args', {})
        settings.setdefault('procedure_fmt', '%(geo_col)s')
        settings.setdefault('select_params', [])
        #############################################################################
        # NOTE: Added for MSSql
        settings.setdefault('method_call', False)
        #############################################################################

        connection = connections[self.db]
        backend = connection.ops

        # Performing setup for the spatial column, unless told not to.
        if settings.get('setup', True):
            default_args, geo_field = self._spatial_setup(att, desc=settings['desc'], field_name=field_name,
                                                          geo_field_type=settings.get('geo_field_type', None))
            for k, v in six.iteritems(default_args):
                settings['procedure_args'].setdefault(k, v)
        else:
            geo_field = settings['geo_field']

        # The attribute to attach to the model.
        if not isinstance(model_att, six.string_types):
            model_att = att

        # Special handling for any argument that is a geometry.
        for name in settings['geom_args']:
            # Using the field's get_placeholder() routine to get any needed
            # transformation SQL.
            geom = geo_field.get_prep_value(settings['procedure_args'][name])
            params = geo_field.get_db_prep_lookup('contains', geom, connection=connection)
            geom_placeholder = geo_field.get_placeholder(geom, connection)

            # Replacing the procedure format with that of any needed
            # transformation SQL.
            old_fmt = '%%(%s)s' % name
            new_fmt = geom_placeholder % '%%s'
            settings['procedure_fmt'] = settings['procedure_fmt'].replace(old_fmt, new_fmt)
            settings['select_params'].extend(params)

        # Getting the format for the stored procedure.

        #############################################################################
        # NOTE: Updated for MSSql
        if settings['method_call']:
            fmt = '%%(geo_col)s.%%(function)s(%s)' % settings['procedure_fmt']
        else:
            fmt = '%%(function)s(%s)' % settings['procedure_fmt']
        #############################################################################

        # If the result of this function needs to be converted.
        if settings.get('select_field', False):
            sel_fld = settings['select_field']
            if isinstance(sel_fld, GeomField) and backend.select:
                self.query.custom_select[model_att] = backend.select
            if connection.ops.oracle:
                sel_fld.empty_strings_allowed = False
            self.query.extra_select_fields[model_att] = sel_fld

        # Finally, setting the extra selection attribute with
        # the format string expanded with the stored procedure
        # arguments.
        return self.extra(select={model_att: fmt % settings['procedure_args']},
                          select_params=settings['select_params'])


class MSSqlGeoManager(GeoManager):

    def get_queryset(self):
        return MSSqlGeoQuerySet(self.model, using=self._db)
