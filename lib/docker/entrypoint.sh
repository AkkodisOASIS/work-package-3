#!/bin/sh

rm -f /tmp/.X1-lock /tmp/.X11-unix/X1 2>/dev/null || true

vncserver :1 \
    -geometry ${GEOMETRY:-1920x1080} \
    -depth    ${DEPTH:-24} \
    -localhost no 

tail -f /dev/null