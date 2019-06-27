# Scrapy doesn't build on current NixOS release-19.03, so explicitly specify
# the last version where it worked. This is good for reproducibility anyway, so
# I'm okay with it.
# https://hydra.nixos.org/job/nixos/release-19.03/nixpkgs.python37Packages.scrapy.x86_64-linux
with import (fetchTarball https://github.com/NixOS/nixpkgs-channels/archive/250988109b295ea91e7ba2606de5eb69569241ce.tar.gz) {};

let
  python = python3;

  sgmllib3k = python.pkgs.buildPythonPackage rec {
    pname = "sgmllib3k";
    version = "1.0.0";

    src = python.pkgs.fetchPypi {
      inherit pname version;
      sha256 = "1s8jm3dgqabgf8x96931scji679qkhvczlv3qld4qxpsicfgns3q";
    };

    # setup.py has the test suite configured incorrectly
    doCheck = false;
  };
in (python.withPackages (ps: [
  ps.feedparser
  # feedparser needs sgmllib for some feeds but nixpkgs doesn't know that yet
  sgmllib3k

  ps.scrapy
  ps.tornado_4

  # pip is only required for `pip freeze > requirements.txt`
  ps.pip
])).env
