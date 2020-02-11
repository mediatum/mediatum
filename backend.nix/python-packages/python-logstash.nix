{ buildPythonPackage
, fetchurl
}:

buildPythonPackage {
  name = "python-logstash-0.4.6";
  src = fetchurl {
    url = "https://pypi.python.org/packages/source/p/python-logstash/python-logstash-0.4.6.tar.gz";
    sha256 = "13763yx0k655y0c8gxv7jj6cqp45zypx2fmnc56jnn9zz1fkx50h";
  };
}
