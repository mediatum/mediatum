# -*- coding: utf-8 -*-
#  mediatum - a multimedia content repository
# taken from https://bitbucket.org/jaraco/backports.functools_lru_cache


from collections import namedtuple
from functools import update_wrapper
import locks as _utils_locks

_CacheInfo = namedtuple("CacheInfo", ["hits", "misses", "maxsize", "currsize"])


class _HashedSeq(list):
    __slots__ = 'hashvalue'

    def __init__(self, tup, hash=hash):
        self[:] = tup
        self.hashvalue = hash(tup)

    def __hash__(self):
        return self.hashvalue


def _make_key(args, kwds, typed,
              kwd_mark=(object(),),
              fasttypes=set([int, str, frozenset, type(None)]),
              sorted=sorted, tuple=tuple, type=type, len=len):
    'Make a cache key from optionally typed positional and keyword arguments'
    key = args
    if kwds:
        sorted_items = sorted(kwds.items())
        key += kwd_mark
        for item in sorted_items:
            key += item
    if typed:
        key += tuple(type(v) for v in args)
        if kwds:
            key += tuple(type(v) for k, v in sorted_items)
    elif len(key) == 1 and type(key[0]) in fasttypes:
        return key[0]
    return _HashedSeq(key)


def lru_cache(maxsize=100, typed=False):
    """Least-recently-used cache decorator.

    If *maxsize* is set to None, the LRU features are disabled and the cache
    can grow without bound.

    If *typed* is True, arguments of different types will be cached separately.
    For example, f(3.0) and f(3) will be treated as distinct calls with
    distinct results.

    Arguments to the cached function must be hashable.

    View the cache statistics named tuple (hits, misses, maxsize, currsize) with
    f.cache_info().  Clear the cache and statistics with f.cache_clear().
    Access the underlying function with f.__wrapped__.

    See:  http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    """

    # Users should only access the lru_cache through its public API:
    #       cache_info, cache_clear, and f.__wrapped__
    # The internals of the lru_cache are encapsulated for thread safety and
    # to allow the implementation to change (including a possible C version).

    def decorating_function(user_function):

        cache = dict()
        stats = [0, 0]                  # make statistics updateable non-locally
        HITS, MISSES = 0, 1             # names for the stats fields
        make_key = _make_key
        cache_get = cache.get           # bound method to lookup key or return None
        _len = len                      # localize the global len() function
        root = []                       # root of the circular doubly linked list
        root[:] = [root, root, None, None]      # initialize by pointing to self
        nonlocal_root = [root]                  # make updateable non-locally
        PREV, NEXT, KEY, RESULT = 0, 1, 2, 3    # names for the link fields

        def make_wrapper(func):
            if maxsize == 0:

                def wrapper(*args, **kwds):
                    # no caching, just do a statistics update after a successful call
                    result = func(*args, **kwds)
                    stats[MISSES] += 1
                    return result

            elif maxsize is None:

                def wrapper(*args, **kwds):
                    # simple caching without ordering or size limit
                    key = make_key(args, kwds, typed)
                    result = cache_get(key, root)   # root used here as a unique not-found sentinel
                    if result is not root:
                        stats[HITS] += 1
                        return result
                    result = func(*args, **kwds)
                    cache[key] = result
                    stats[MISSES] += 1
                    return result

            else:

                def wrapper(*args, **kwds):
                    # size limited caching that tracks accesses by recency
                    key = make_key(args, kwds, typed) if kwds or typed else args
                    with _utils_locks.named_lock("lrucachelock"):
                        link = cache_get(key)
                        if link is not None:
                            # record recent use of the key by moving it to the front of the list
                            root, = nonlocal_root
                            link_prev, link_next, key, result = link
                            link_prev[NEXT] = link_next
                            link_next[PREV] = link_prev
                            last = root[PREV]
                            last[NEXT] = root[PREV] = link
                            link[PREV] = last
                            link[NEXT] = root
                            stats[HITS] += 1
                            return result
                    result = func(*args, **kwds)
                    with _utils_locks.named_lock("lrucachelock"):
                        root, = nonlocal_root
                        if key in cache:
                            # getting here means that this same key was added to the
                            # cache while the lock was released.  since the link
                            # update is already done, we need only return the
                            # computed result and update the count of misses.
                            pass
                        elif _len(cache) >= maxsize:
                            # use the old root to store the new key and result
                            oldroot = root
                            oldroot[KEY] = key
                            oldroot[RESULT] = result
                            # empty the oldest link and make it the new root
                            root = nonlocal_root[0] = oldroot[NEXT]
                            oldkey = root[KEY]
                            root[KEY] = root[RESULT] = None
                            # now update the cache dictionary for the new links
                            del cache[oldkey]
                            cache[key] = oldroot
                        else:
                            # put result in a new link at the front of the list
                            last = root[PREV]
                            link = [last, root, key, result]
                            last[NEXT] = root[PREV] = cache[key] = link
                        stats[MISSES] += 1
                    return result

            return wrapper

        def cache_info():
            """Report cache statistics"""
            with _utils_locks.named_lock("lrucachelock"):
                return _CacheInfo(stats[HITS], stats[MISSES], maxsize, len(cache))

        def cache_clear():
            """Clear the cache and cache statistics"""
            with _utils_locks.named_lock("lrucachelock"):
                cache.clear()
                root = nonlocal_root[0]
                root[:] = [root, root, None, None]
                stats[:] = [0, 0]

        def cache_remove(*args, **kwds):
            """Removes result which is cached for *args, **kwds"""
            key = make_key(args, kwds, typed) if kwds or typed else args
            link = cache_get(key)
            link_prev, link_next, key, _ = link
            with _utils_locks.named_lock("lrucachelock"):
                # set next field of prev
                link_prev[NEXT] = link_next
                link_next[PREV] = link_prev
                # remove link
                del cache[key]

        def cache_add(obj, *args, **kwds):
            """Adds a result for *args, **kwds"""
            local_wrapper = make_wrapper(lambda *a, **k: obj)
            local_wrapper(*args, **kwds)

        def make_graph(filename):
            import objgraph

            def extra_info(o):
                if isinstance(o, dict):
                    return o.keys()
                else:  # list
                    return "id={} val={}\nprev={} next={}".format(hex(id(o)), o[RESULT], o[PREV][RESULT], o[NEXT][RESULT])

            objgraph.show_refs([cache, nonlocal_root[0]], filename=filename,
                               refcounts=True,
                               max_depth=10,
                               filter=lambda o: isinstance(o, (dict, list)),
                               highlight=lambda o: o is nonlocal_root[0],
                               too_many=maxsize or 100000,
                               extra_info=extra_info)

        wrapper = make_wrapper(user_function)
        wrapper.__wrapped__ = user_function
        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        wrapper.cache_remove = cache_remove
        wrapper.cache_add = cache_add
        wrapper.make_graph = make_graph
        wrapper._cache = cache
        return update_wrapper(wrapper, user_function)

    return decorating_function


if __name__ == "__main__":

    @lru_cache(maxsize=3)
    def f(a):
        return a

    print f(1), f.cache_info()
    f.make_graph("1.png")
    print f(2), f.cache_info()
    f.make_graph("2.png")
    print f(3), f.cache_info()
    f.make_graph("3a.png")
    print f(1), f.cache_info()
    print f(2), f.cache_info()
    print f(3), f.cache_info()
    f.make_graph("3b.png")
    print f(4), f.cache_info()
    f.make_graph("4.png")
    print f(5), f.cache_info()
    f.make_graph("5a.png")

    f.cache_remove(4)
    f.cache_info()
    f.make_graph("5b.png")
    print f(4), f.cache_info()
    print f(4), f.cache_info()
    f.make_graph("5c.png")

    print f(6), f.cache_info()
    print f(7), f.cache_info()
    print f(8), f.cache_info()
    print f(8), f.cache_info()

    f.make_graph("8.png")

    print f(9), f.cache_info()
    f.make_graph("9.png")

    f.cache_add(10, 10)
    f.make_graph("10.png")
    pass
