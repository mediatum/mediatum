Database Migrations
===================

Upgrade From MySQL To PostgreSQL Version
========================================

Must be done once when upgrading to a PostgreSQL version of mediaTUM.
See `README_MYSQL-TO-POSTGRES.md`.


PostgreSQL Migrations
=====================

Migrations between newer mediaTUM versions are done with [Alembic](http://alembic.readthedocs.org/en/latest/index.html).
For a normal upgrade, running `bin/manage.py schema upgrade` is sufficient.
For advanced migrations like downgrades, refer to the [Alembic documentation](http://alembic.readthedocs.org/en/latest/index.html).


