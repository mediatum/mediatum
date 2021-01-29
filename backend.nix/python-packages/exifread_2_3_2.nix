{ stdenv
, buildPythonPackage
, fetchPypi
}:

buildPythonPackage rec {
  pname = "ExifRead";
  version = "2.3.2";

  src = fetchPypi {
    inherit pname version;
    sha256 = "0rhpsmi7c41lxclbm1nw4vq8jv6h4vz0x65w7f4d6s010kslmxx0";
  };
}
