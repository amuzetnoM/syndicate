#!/usr/bin/env bash
# Helper: move Docker Compose bind-mount data to a dedicated data disk
# Usage: sudo ./move_docker_data.sh /mnt/newdisk/syndicate/docker-data

set -euo pipefail

DEST=${1:-/mnt/newdisk/syndicate/docker-data}
SRC_DIR=$(pwd)/docker-data

echo "Destination: $DEST"
echo "Source (repo): $SRC_DIR"

if [ ! -d "$DEST" ]; then
  echo "Creating destination directory $DEST (requires sudo)"
  sudo mkdir -p "$DEST"
  sudo chown $(id -u):$(id -g) "$DEST"
fi

echo "Copying existing repo docker-data to destination (preserving perms)"
sudo rsync -a --progress "$SRC_DIR/" "$DEST/"

echo "Updating docker-compose.yml to reference absolute path"
echo "(This script will not modify files automatically; update your compose file or set an env variable)")

cat <<'EOF'
Example docker-compose volume entry (use absolute path):
  - /mnt/newdisk/syndicate/docker-data/gost_data:/app/data
EOF

echo "Done. Ensure permissions and SELinux contexts (if applicable) are correct."
