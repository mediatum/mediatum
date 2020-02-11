{ buildPythonPackage
, fetchurl
}:

buildPythonPackage {
  name = "imagesize-0.7.1";
  src = fetchurl {
    url = "https://pypi.python.org/packages/53/72/6c6f1e787d9cab2cc733cf042f125abec07209a58308831c9f292504e826/imagesize-0.7.1.tar.gz";
    sha256 = "0ab2c62b87987e3252f89d30b7cedbec12a01af9274af9ffa48108f2c13c6062";
  };
  doCheck = false;
}
