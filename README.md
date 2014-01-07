Basic GIS (geodjango) support for Microsoft SQL Server, built on top
of [django-pyodbc-azure](https://github.com/michiya/django-pyodbc-azure)

# Limitations of SQL Server

SQL Server is OGC compliant, but does fall short of the functionality
provided by [PostGIS](http://postgis.net/) and
[Oracle Spatial](http://www.oracle.com/technetwork/database/options/spatialandgraph/overview/index.html).
In particular, all of the boundary inclusion operations are missing:
for example,
[`contains`](https://docs.djangoproject.com/en/dev/ref/contrib/gis/geoquerysets/#contains)
is supported, but not
[`covers`](https://docs.djangoproject.com/en/dev/ref/contrib/gis/geoquerysets/#covers).

Type information is also slightly different in SQL Server.  Instead of
keeping the geometry type (Point, Polygon, etc) in the column's
metadata, it is a property of the *instance* (and hence so is the
dimensionality), and similarly for the SRID.  This means you can in
theory store geometries of different types and SRIDs in the same
column; this driver creates a constraint to check the type, but
nothing else.  It also means that introspection is rather fragile.

Geometries cannot be transformed to a different SRID (such as with
[`ST_Transform`](http://postgis.org/docs/ST_Transform.html)) in
PostGIS.

# TODO

* aggregate operations support
* geography support
* extended operations (gml, geojson, etc)
