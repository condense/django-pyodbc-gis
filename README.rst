This driver implements basic GIS (geodjango) support for Microsoft SQL
Server, built on top of `django-pyodbc-azure`_.

.. _django-pyodbc-azure: https://github.com/michiya/django-pyodbc-azure

It should be considered very alpha-quality at this stage!  Feedback,
issues, and patches are all very welcome.

======================================
 Supported and unsupported operations
======================================

Most `possible operations`_ are supported.  The primary exceptions are
those that include the boundary itself, and convenience operations
such as ``left``/``right``, ``overlaps_above``, etc.

.. _possible operations: https://docs.djangoproject.com/en/dev/ref/contrib/gis/geoquerysets/

The following spatial lookups are **not** supported:

* bounding-box related: ``contains_properly``, ``covered_by``, ``covers``
* specialist positional: ``left``, ``right``, ``overlaps_left``,
  ``overlaps_right``, ``overlaps_above``, ``overlaps_below``,
  ``strictly_above``, ``strictly_below``
* miscellaneous: ``dwithin``, ``exact``, ``relate``, ``same_as``

The following spatial aggregate operations are **not** supported:

* ``extent3d`` and ``make_line``

In addition, for performance reasons not all geometry operations have
a corresponding geography analogue.  The following operations are
**not** available on geography types:

* ``bbcontains``, ``bboverlaps``, ``contained``, ``crosses``, ``touches``

===========================
 Limitations of SQL Server
===========================

SQL Server is OGC compliant, but  does fall short of the functionality
provided by PostGIS_ and `Oracle Spatial`_.  In particular, all of the
boundary inclusion operations are missing: for example, `contains`_ is
supported, but not `covers`_.

.. _PostGIS: http://postgis.net/
.. _Oracle Spatial: http://www.oracle.com/technetwork/database/options/spatialandgraph/overview/index.html
.. _contains: https://docs.djangoproject.com/en/dev/ref/contrib/gis/geoquerysets/#contains
.. _covers: https://docs.djangoproject.com/en/dev/ref/contrib/gis/geoquerysets/#covers

Type information is also slightly different in SQL Server.  Instead of
keeping the geometry type (Point, Polygon, etc) in the column's
metadata, it is a property of the *instance* (and hence so is the
dimensionality), and similarly for the SRID.  This means you can in
theory store geometries of different types and SRIDs in the same
column; this driver creates a constraint to check the type, but
nothing else.  It also means that introspection is rather fragile.

Geometries cannot be transformed to a different SRID (such as with
`ST_Transform`_ in PostGIS).

.. _ST_Transform: http://postgis.org/docs/ST_Transform.html

=================
 Admin Interface
=================

The admin interface works.  This is worth noting here simply because
the interface has to be pretend to be MySQL in order to run!  There
are some hard-coded checks for MySQL in the framework, and the
limitations (with respect to introspection) of SQL Server are actually
similar enough that this works for SQL Server too.

========================
 Installation and Setup
========================

The only direct dependency is `django-pyodbc-azure`_.  If you are on
linux this will require installing freetds_ and odbcinst_.  You will
also need to configure_ it (the most important is ``odbcinst.ini``).

.. _django-pyodbc-azure: https://github.com/michiya/django-pyodbc-azure
.. _freetds: http://www.freetds.org/
.. _odbcinst: http://www.unixodbc.org/
.. _configure: http://www.unixodbc.org/doc/FreeTDS.html

To use the driver, your Django database configuration section should
look something like this: ::

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

You have two options regarding specifying the host connection details;
if you have configured a DSN you may omit the ``HOST`` key and use the
``dsn`` key in ``OPTIONS`` to specify it.  If not, you will probably
need to specify the TDS version in ``extra_params`` (if you get error
messages about unicode_ you may well have gotten this wrong)

.. _unicode: http://www.seanelavelle.com/2011/07/30/pyodbc-and-freetds-unicode-ntext-problem-solved/

======
 TODO
======

* extended operations (gml, geojson, etc.  Further investigation: SQL
  Server only supports GML, but treats it as an instance method
  where-as geodjango assumes it is a function.  This might remain on
  the back-burner for now)
* Check inspectdb support
* Test suite!
  - Test against 2008, 2005 as well
