MySQL Migration
===============

[pgloader](http://pgloader.io) is used for migrating an old mysql mediaTUM database to PostgreSQL.
The pgloader .load script will import all contents from MySQL into the PostgreSQL scheme 'mediatum\_import'
and run the conversion SQL script. 

Steps
-----

1. set PostgrSQL database connection options in `mediatum.cfg`
2. run `ipython bin/manage.py create`
3. Copy `migration/mysql_migration.load.example` to `migration/mysql_migration.load`
4. Edit `mysql_migration.load`, set the connection strings and postgres options
5. run pgloader: `pgloader --verbose mysql_migration.load`
6. For better performance, run `ipython bin/manage.py analyze_reindex`
