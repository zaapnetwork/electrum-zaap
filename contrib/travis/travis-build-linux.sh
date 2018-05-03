#!/bin/bash
BUILD_REPO_URL=https://github.com/akhavr/electrum-zaap.git

cd build

if [[ -z $TRAVIS_TAG ]]; then
  exit 0
else
  git clone --branch $TRAVIS_TAG $BUILD_REPO_URL electrum-zaap
fi

docker run --rm -v $(pwd):/opt -w /opt/electrum-zaap -t akhavr/electrum-zaap-release:Linux /opt/build_linux.sh
docker run --rm -v $(pwd):/opt -v $(pwd)/electrum-zaap/:/root/.wine/drive_c/electrum -w /opt/electrum-zaap -t akhavr/electrum-zaap-release:Wine /opt/build_wine.sh
