{ buildPythonPackage
, fetchFromGitHub
}:

buildPythonPackage {
  name = "pygeoip-0.1.3";
  src = fetchFromGitHub {
    repo = "pygeoip";
    owner = "simplegeo";
    rev = "hudson-pygeoip-1";
    sha256 = "1k1zgw8c9hdsxm6aj50mgd8b0jsybx6nd4px0s3bgl4a0aqydpx5";
  };
}
