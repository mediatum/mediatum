MySQL To PostgreSQL Migration
=============================

[pgloader](http://pgloader.io) is used for migrating an old mysql mediaTUM database to PostgreSQL.
The pgloader .load script will import all contents from MySQL into the PostgreSQL scheme 'mediatum\_import'.

Steps
-----

1. set PostgresSQL database connection options in `mediatum.cfg`
2. run `ipython bin/manage.py schema create` to set up the database structure
3. run `ipython bin/manage.py iplist name_of_iplist < iplist.txt` to import IP lists for the permission system.
3. Copy `migration/mysql_migration.load.example` to `migration/mysql_migration.load`
4. Edit `mysql_migration.load`, set the connection strings and postgres options
4.1 If you don't have pgloader on your system, you can use the docker container. See `python bin/mysql_migrate.py --help` for more info.
5. Copy data from mysql to PostgreSQL database with `ipython bin/mysql_migrate.py pgloader`
6. Do the database schema migration in Postgres: `ipython bin/mysql_migrate.py schema_migration`
7. For better performance, run `ipython bin/manage.py analyze_reindex`
