{ buildPythonPackage
, fetchurl
}:

buildPythonPackage {
  name = "snowballstemmer-1.2.1";
  src = fetchurl {
    url = "https://pypi.python.org/packages/20/6b/d2a7cb176d4d664d94a6debf52cd8dbae1f7203c8e42426daa077051d59c/snowballstemmer-1.2.1.tar.gz";
    sha256 = "919f26a68b2c17a7634da993d91339e288964f93c274f1343e3bbbe2096e1128";
  };
  doCheck = false;
}
