{ buildPythonPackage
, fetchurl
}:

buildPythonPackage {
  name = "mediatumtal-0.3.2";
  src = fetchurl {
    url = "https://pypi.python.org/packages/source/m/mediatumtal/mediatumtal-0.3.2.tar.gz";
    sha256 = "07vixbpv0a7dv0y64nsyz4ff98s5jgin6isshai7ng1xbnj4xbxs";
  };
}
