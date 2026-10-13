#!/bin/bash

# Pour debian 13

echo 'deb http://download.opensuse.org/repositories/science:/dlr/Debian_13/ /' \
  | tee /etc/apt/sources.list.d/science:dlr.list
 
curl -fsSL https://download.opensuse.org/repositories/science:dlr/Debian_13/Release.key \
  | gpg --dearmor \
  | tee /etc/apt/trusted.gpg.d/science_dlr.gpg > /dev/null

apt update -y && apt install sumo -y