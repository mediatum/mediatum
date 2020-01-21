{ pkgs ? (import ./nixpkgs.nix {}).pkgs
, fetchurl ? pkgs.fetchurl
, pcre ? pkgs.pcre
, python2Packages ? pkgs.python2Packages
}:

python2Packages.buildPythonPackage rec {
  name = "uwsgi-2.0.18";
  src = fetchurl {
    url = "http://projects.unbit.it/downloads/${name}.tar.gz";
    sha256 = "1zvj28wp3c1hacpd4c6ra5ilwvvfq3l8y6gn8i7mnncpddlzjbjp";
  };
  doCheck = false;
  propagatedBuildInputs = [ pcre ];
}
