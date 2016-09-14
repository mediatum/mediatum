# Legacy German Umlaut Handling 

To reproduce the old search behaviour concerning German umlauts from previous mediaTUM versions, you can use 
a special full text search dictionary based on the unaccent Postgres extension. 
This dictionary replaces ß with ss, ü with ue and so on.

In order to use it, put the file `unaccent_german_umlauts_special.rules` into $SHAREDIR/tsearch_data/.

Now, you can create the search dictionary and configuration:

    CREATE extension unaccent SCHEMA public;
    CREATE TEXT SEARCH DICTIONARY unaccent_german_umlauts (template=public.unaccent, rules='unaccent_german_umlauts_special');
    CREATE TEXT SEARCH CONFIGURATION simple_unaccent_german_umlauts (copy = simple);
    ALTER TEXT SEARCH CONFIGURATION simple_unaccent_german_umlauts ALTER MAPPING FOR word,hword,hword_part WITH unaccent_german_umlauts, simple;


This new search configuration can be selected in the `mediatum.cfg` config file:

[search]
attribute_autoindex_languages=german,english,simple_unaccent_german_umlauts
service_languages=simple_unaccent_german_umlauts

