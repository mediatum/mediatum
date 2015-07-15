MySQL Migration
===============

[pgloader](http://pgloader.io) is used for migrating an old mysql mediaTUM database to PostgreSQL.
The pgloader .load script will import all contents from MySQL into the PostgreSQL scheme 'mediatum\_import'.

Steps
-----

1. set PostgrSQL database connection options in `mediatum.cfg`
2. run `ipython bin/manage.py create` to set up the database structure
3. Copy `migration/mysql_migration.load.example` to `migration/mysql_migration.load`
4. Edit `mysql_migration.load`, set the connection strings and postgres options
4.1 If you don't have pgloader on your system, you can use the docker container. See `python bin/mysql_migration.py --help` for more info.
5. run migration with `ipython bin/mysql_migration.py everything`
6. For better performance, run `ipython bin/manage.py analyze_reindex`
