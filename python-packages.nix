{
  pygments = self.buildPythonPackage {
    name = "pygments-2.0.2";
    src = fetchurl {
      url = "https://pypi.python.org/packages/source/P/Pygments/Pygments-2.0.2.tar.gz";
      md5 = "238587a1370d62405edabd0794b3ec4a";
    };
    propagatedBuildInputs = with self; [];
    buildInputs = with self; [];
    doCheck = false;
  };

### Test requirements

  
}
