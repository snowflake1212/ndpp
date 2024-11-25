#!/bin/bash
echo "Changing nameserver..."
echo "nameserver 8.8.8.8" | tee /etc/resolv.conf > /dev/null

# Restart Grass Node
pkill -f rvpdn.py &&
echo "Killing openvpn..."
killall openvpn
sleep 5
rm -f rvpdn.py &&
wget https://raw.githubusercontent.com/snowflake1212/ndpp/refs/heads/main/rvpdn.py &&
chmod +x rvpdn.py
python3 rvpdn.py JP KR &
sleep 20

echo "Running grass.py..."
pkill -f npbot.py
python3 npbot.py &
