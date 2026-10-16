#!/usr/bin/env bash
# One-time setup on a fresh Raspberry Pi OS 64-bit (user: raspberrypi). Run from the repo root: ./setup_pi.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"

sudo apt update && sudo apt full-upgrade -y
sudo apt install -y git python3-venv i2c-tools
sudo raspi-config nonint do_i2c 0   # enable I2C
sudo usermod -aG i2c "$(whoami)"

command -v tailscale >/dev/null || curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

python3 -m venv "$REPO/venv"
"$REPO/venv/bin/pip" install eclipse-zenoh==1.10.1   # must match zenohd on RPI1

sudo cp "$REPO/wtp-rpi2.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wtp-rpi2

echo
echo "Atlas EZO devices on I2C bus 1:"
i2cdetect -y 1 || true
echo "Can we reach RPI1's zenoh router?"
timeout 3 bash -c '</dev/tcp/100.104.48.38/7447' && echo "  yes" || echo "  NO - check tailscale on both Pis"
echo "Now: sudo reboot"
