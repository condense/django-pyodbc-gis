This driver implements basic GIS (geodjango) support for Microsoft SQL
Server, built on top of
[django-pyodbc-azure](https://github.com/michiya/django-pyodbc-azure).

It should be considered very alpha-quality at this stage!  Feedback,
issues, and patches are all very welcome.

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
[`ST_Transform`](http://postgis.org/docs/ST_Transform.html) in
PostGIS).

# Installation and Setup

The only direct dependency is
[django-pyodbc-azure](https://github.com/michiya/django-pyodbc-azure).
If you are on linux this will require installing
[freetds](http://www.freetds.org/) and
[odbcinst](http://www.unixodbc.org/).  You will also need to
[configure](http://www.unixodbc.org/doc/FreeTDS.html) it (the most
important is `odbcinst.ini`).

To use the driver, your Django database configuration section should
look something like this:
```
DATABASES = {
    'default': {
        'NAME': 'dbname',
        'ENGINE': 'django_pyodbc_gis',
        'HOST': '127.0.0.1,1433',
        'USER': 'django',
        'PASSWORD': 'pwd123',
        'OPTIONS': {
            'host_is_server': True,
            # 'dsn': 'mssql',
            'extra_params': 'TDS_Version=8.0'
        }
    }
}
```

You have two options regarding specifying the host connection details;
if you have configured a DSN you may omit the `HOST` key and use the
`dsn` key in `OPTIONS` to specify it.  If not, you will probably need
to specify the TDS version in `extra_params` (if you get error
messages about
[unicode](http://www.seanelavelle.com/2011/07/30/pyodbc-and-freetds-unicode-ntext-problem-solved/)
you may well have gotten this wrong)

# TODO

* Other distance functions (`distance_lt`, etc)
* aggregate operations support
* geography support
* extended operations (gml, geojson, etc)
