{ buildPythonPackage
, fetchurl
}:

buildPythonPackage {
  name = "mutagen-1.19";
  src = fetchurl {
    url = "https://salix.enialis.net/x86_64/13.1/source/l/mutagen/mutagen-1.19.tar.gz";
    sha256 = "19jgwpgc5vbwwm714kv40gy09rcag4s4v63kqkmd9n6838wxawl0";
  };
}
