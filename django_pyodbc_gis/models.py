"""
 The GeometryColumns and SpatialRefSys models for the PostGIS backend.
"""
from django.db import models
from django.contrib.gis.db.backends.base import SpatialRefSysMixin
from django.utils.encoding import python_2_unicode_compatible


class SpatialRefSys(models.Model, SpatialRefSysMixin):
    """
    Based on sys.spatial_reference_systems

    We're ignoring an inconvenient truth.  The table definition
    doesn't include a primary key and srid is defined to allow nulls.
    We're calling their bluff on this.
    """
    srid = models.IntegerField(primary_key=True, db_column='spatial_reference_id')
    auth_name = models.CharField(max_length=128, null=True, db_column='authority_name')
    auth_srid = models.IntegerField(null=True, db_column='authorized_spatial_reference_id')
    well_known_text = models.CharField(max_length=4000, null=True)
    unit_of_measure = models.CharField(max_length=128, null=True)
    unit_conversion_factor = models.FloatField(null=True)

    class Meta:
        db_table = '[sys].[spatial_reference_systems]'
        managed = False

    @property
    def wkt(self):
        return self.well_known_text

    @classmethod
    def wkt_col(cls):
        return 'well_known_text'
