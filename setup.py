import os
from setuptools import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="django-pyodbc-gis",
    version="0.0.5",
    author="Mark Hepburn",
    author_email="mark@condense.com.au",
    description=("GIS support for SQL Server, on top of django-pyodbc-azure"),
    license="BSD",
    keywords="django mssql gis",
    url="https://www.github.com/condense/django-pyodbc-gis",
    packages=['django_pyodbc_gis'],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 1 - Planning",
        "Topic :: Database",
        "License :: OSI Approved :: BSD License",
    ],
    install_requires=[
        "django-pyodbc-azure",
    ],
)
