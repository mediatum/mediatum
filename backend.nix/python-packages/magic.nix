{ buildPythonPackage
, fetchurl
, python
, file
}:

buildPythonPackage {
  name = "${file.name}";
  src = file.src;
  patchPhase = ''
    substituteInPlace python/magic.py --replace "find_library('magic')" "'${file}/lib/libmagic.so'"
  '';
  buildInputs = [ python file ];
  preConfigure = "cd python";
  doCheck = false;
}
