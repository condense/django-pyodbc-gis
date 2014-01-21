"""
 The GeometryColumns and SpatialRefSys models for the PostGIS backend.
"""
from django.db import models
from django.contrib.gis.db.backends.base import SpatialRefSysMixin
from django.utils.encoding import python_2_unicode_compatible


class SpatialRefSys(models.Model, SpatialRefSysMixin):
    """
    Based on sys.spatial_reference_systems

    We're ignoring an inconvenient truth here.  The table definition
    doesn't report a primary key and srid is defined to allow nulls
    so we decided to call their bluff.
    """
    srid = models.IntegerField(primary_key=True, db_column='spatial_reference_id')
    auth_name = models.CharField(max_length=128, null=True, db_column='authority_name')
    auth_srid = models.IntegerField(null=True, db_column='authorized_spatial_reference_id')
    well_known_text = models.CharField(max_length=4000, null=True, db_column='well_known_text')
    unit_of_measure = models.CharField(max_length=128, null=True)
    unit_conversion_factor = models.FloatField(null=True)

    class Meta:
        db_table = '[sys].[spatial_reference_systems]'
        managed = False

    @property
    def wkt(self):
        #
        # NOTE: This patches the WKT format to get it working for GDAL.
        #
        # The Well-known text format seems to require SPHEROID but
        # does indicate 'the terms "spheroid" and "ellipsoid" are
        # synonymous' so perhaps GDAL is being a little strict.
        #
        # http://www.opengeospatial.org/standards/sfs (PDF)
        # http://www.geoapi.org/3.0/javadoc/org/opengis/referencing/doc-files/WKT.html#SPHEROID
        #
        return self.well_known_text.replace("ELLIPSOID", "SPHEROID")

    #
    # NOTE: We're massaging the unit name to avoid case sensitivties of
    # GeometryField.geodetic().  It's a moving target task because of the case
    # sensitivities in the definition (shown below).
    #
    #   geodetic_units = ('Decimal Degree', 'degree')
    #
    # This hack should be removed when the bug is fixed.
    #
    # https://docs.djangoproject.com/en/dev/ref/contrib/gis/measure/#supported-units
    #
    @property
    def units(self):
        num, name = super(SpatialRefSys, self).units
        if name.lower() == 'decimal degree':
            name = 'Decimal Degree'
        else:
            name = name.lower()
        return (num, name)

    #
    # TODO: Is this important?  Am I doing it right?
    #
    @classmethod
    def wkt_col(cls):
        return 'well_known_text'
