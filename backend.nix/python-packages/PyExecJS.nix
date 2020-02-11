{ buildPythonPackage
, fetchurl
, six
}:

buildPythonPackage {
  name = "PyExecJS-1.5.1";
  src = fetchurl {
    url = "https://pypi.python.org/packages/ba/8e/aedef81641c8dca6fd0fb7294de5bed9c45f3397d67fddf755c1042c2642/PyExecJS-1.5.1.tar.gz";
    sha256 = "0p2hkxv7mzxvbw6c0217r68shmw13zbhmp3vzy1q34bn143ivk1l";
  };
  propagatedBuildInputs = [ six ];
  doCheck = false;
}
