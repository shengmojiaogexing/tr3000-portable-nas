#!/bin/sh
ip -6 addr show scope global | awk '/inet6 2[0-9a-f]{3}:/{gsub(/\/.*/,"",$2); print $2; exit}'
