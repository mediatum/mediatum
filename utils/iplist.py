#!/usr/bin/env python


"""
This module converts ip address lists into ipaddr Network objects,
which in turn can be fed into mediatum for access control.
Lists may consist of strings of the form "12.12.12.12-12.12.12.34/32".
Common usage pattern is to parse a list with ipranges_to_ipobjects,
followed by update_mediatum_iplist to store the list in the database.
"""


# Terminology here:
#  * ipobject : something like ipaddr.IPAddress or ipaddr.IPNetwork
#  * iprange : a string that represents a range of ip addresses
#  * oldiplist : a dictionary containing many ip address ranges;
#                this was used in the old mysql world in tumips.py


from ipaddr import IPAddress, IPNetwork, collapse_address_list
import os.path as _os_path
import re
import sys

sys.path.append(_os_path.normpath(_os_path.join(__file__, "..", "..")))

from core import db
from core.database.postgres.permission import IPNetworkList


def ipranges_to_ipobjects(ranges):
    """
    Parse a list of ip ranges (texts, e.g. "12.12.12.12-12.12.12.34/32")
    and return a (compressed) list of IPNetwork objects.
    Everything beyond a hash ('#') is ignored.
    Malformed lines are also ignored.
    """
    re_ip4range = re.compile(r"""
            ^
            \s*
            (?:(?P<start>\d+\.\d+\.\d+\.\d+)-)?
                 (?P<end>\d+\.\d+\.\d+\.\d+)(?:/(?P<mask>\d+))?
            \s*
            (?:\#.*)?
            $
            """, re.VERBOSE).match
    addresses = list()
    for iprange in ranges:
        # just skip this line if the regex doesn't match
        iprange = re_ip4range(iprange)
        if not iprange:
            continue
        iprange = iprange.groupdict()
        # extract end and (optional) start as IPAddresses
        end = IPAddress(iprange["end"])
        address = IPAddress(iprange["start"] or end)
        assert address <= end
        # turn the mask into a string-format-function
        mask_fmt = "{{}}/{}".format(iprange["mask"] or str(end.max_prefixlen)).format
        # computation of the size of each subnet is hard, so we prefer while over for
        while address <= end:
            addresses.append(IPNetwork(mask_fmt(str(address))))
            address += int(addresses[-1].broadcast)-int(addresses[-1].network)+1
    return tuple(collapse_address_list(addresses))


def ipobjects_to_ipranges(addresses):
    """
    Convert a list of IPNetwork objects into a list of
    strings containing ip ranges as text strings, e.g.,
    "123.123.123.123-123.123.123.234/32" or "123.123.123.123/32".
    """
    # collaps and sort addresses, catch an empty list
    addresses = list(addresses)
    if not addresses:
        return ()
    addresses = collapse_address_list(addresses)
    addresses = sorted(addresses)
    addresses = iter(addresses)
    # prepare conversion loop
    ranges = list()
    fmt = lambda s, e, p: ("{0}/{2}" if s == e else "{0}-{1}/{2}").format(s, e, p)
    start = next(addresses)
    end = start.broadcast  # last address of current range
    start = start.network  # first address of current range
    for current in addresses:
        # combine consecutive ranges if possible
        if (end+1 < current.network):
            ranges.append(fmt(start, end, 32))
            start = current.network
        end = current.broadcast
    # add final range
    ranges.append(fmt(start, end, 32))
    return tuple(ranges)


def update_mediatum_iplist(name, addresses):
    """
    Create or update the IPNetworkList with give
    name with the ip objects in 'addresses'.
    """
    iplist = db.query(IPNetworkList).filter(IPNetworkList.name == name).scalar()
    if not iplist:
        iplist = IPNetworkList(name=name)
        db.session.add(iplist)
    iplist.subnets = addresses
    db.session.commit()


def get_mediatum_iplist(name):
    """
    Fetch the IPNetworkList with given name
    and return its subnets list of ip ranges.
    """
    query = db.query(IPNetworkList).filter(IPNetworkList.name == name)
    return query.one().subnets


def oldiplist_to_ipranges(ips):
    """
    Take an ip list in the old (mysql-world) format, e.g. a dictionary
    'ips' with prefixes as keys (the first three bytes of an ip address,
    e.g. "123.123.123") and a list of pairs (a,b) as values,
    where 'a' is a possible forth byte of the ip addresses
    and 'b'==1 means all bytes from this one onwards are part of the range,
    but 'b'==0 means all bytes from this one onwards are not included.
    Return a list of strings containing ip ranges as text string, e.g.,
    "123.123.123.123-123.123.123.234/32".
    """
    ranges = list()
    range_fmt = "{pre}.{start}-{pre}.{end}/32".format
    for prefix, suffixes in ips.iteritems():
        # We assume the suffix list is ordered and 1/0
        # in the second field occur alternating.
        assert len(suffixes) % 2 == 0
        # rearrange all suffix entries as pairs
        assert set(b for a, b in suffixes[::2]) == set((1,))
        assert set(b for a, b in suffixes[1::2]) == set((0,))
        suffixes = zip(suffixes[::2], suffixes[1::2])
        for start, end in suffixes:
            assert start[0] <= end[0]
            if start[0] < end[0]:
                ranges.append(range_fmt(pre=prefix, start=start[0], end=end[0]-1))
    return ranges
