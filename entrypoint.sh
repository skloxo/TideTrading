#!/bin/sh
# entrypoint.sh — TideTrading container startup script
# Ensures runtime directories that live on mounted Docker volumes exist before
# Python/mootdx is imported (volume mounts shadow the image-layer mkdir calls).

set -e

# The vt-home volume is mounted at /home/tide/.tide-trading.
# The image layer creates /home/tide/.tide-trading/.mootdx, but after the volume
# mount Docker replaces the directory with an empty external volume, so .mootdx
# is gone. mootdx's config module then hits a FileExistsError (Errno 17) when it
# tries to mkdir the dangling symlink /home/tide/.mootdx -> .tide-trading/.mootdx.
# We recreate the target directory here at every container start.
mkdir -p /home/tide/.tide-trading/.mootdx

exec "$@"
