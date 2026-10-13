#!/bin/bash

echo "---------- [Build - production] ----------"
python3 -m build --wheel -o ./dist

echo "---------- [Nettoyage post_production] ----------"
rm -rf ./build

echo "---------- [Génération de la doc] ----------"
sphinx-build -b html ./sphinx/source ./sphinx/build/
sphinx-build -b singlehtml ./sphinx/source/ ./sphinx/build/singlehtml/

google-chrome \
  --headless \
  --disable-gpu \
  --no-sandbox \
  --disable-setuid-sandbox \
  --disable-dev-shm-usage \
  --no-pdf-header-footer \
  --print-to-pdf=./doc/oasis_wp3_documentation.pdf \
  ./sphinx/build/singlehtml/index.html \
  2>/dev/null

echo "---------- [Nettoyage post-build documentation] ----------"
rm -rf ./sphinx/build

echo "---------- [Build du docker] ----------"
cd .. \
&& docker compose --profile oasis build \
&& docker tag oasisprototype-oasis:latest oasiswp3:1.0.0 \
&& docker save -o ./lib/dist/oasiswp3_1_0_0.tar oasiswp3:1.0.0