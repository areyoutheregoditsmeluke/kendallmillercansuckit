# Copy this file to the ROOT of your badge filesystem as secrets.py
# (not inside any app folder — MonaOS puts this at /secrets.py)
#
# How to copy it:
#   1. Double-press RESET on badge → it mounts as "BADGER" USB drive
#   2. Copy this file onto that drive and rename it secrets.py
#   OR
#   3. mpremote cp secrets.py :secrets.py

WIFI_SSID     = "your-wifi-network-name"
WIFI_PASSWORD = "your-wifi-password"

# Your Pi's local IP address (find it with: hostname -I on the Pi)
# Port 8765 is where pi/server.py listens
PI_HOST = "http://192.168.1.XXX:8765"

# Optional: your GitHub username (used by other badge apps)
GITHUB_USERNAME = "your-github-username"
