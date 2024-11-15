#!/usr/bin/env python3
import requests
import os
import sys
import subprocess
import base64
import time
import re
import glob
import random
import fcntl  # Untuk lock file

# Konfigurasi koneksi
MAX_RETRY_LIMIT = 1  # Batas percobaan koneksi ke setiap server
CONNECTION_TIMEOUT = 10  # Timeout untuk requests.get dalam detik
VPN_CONNECTION_TIMEOUT = 10  # Timeout koneksi untuk memastikan stabilitas
CHECK_IP_TIMEOUT = 5  # Timeout untuk mengecek IP setelah terhubung ke VPN
DEFAULT_IP = "64.181.249.5"  # IP default yang harus dicek setiap 5 menit
LOG_FILE = '/home/python/log_ovpn.txt'  # Lokasi file log di host


# Mengecek argumen input untuk menerima lebih dari satu negara
if len(sys.argv) < 2:
    print('usage: ' + sys.argv[0] + ' [country name | country code]...')
    exit(1)
countries = sys.argv[1:]

# Mengambil data dari VPNGate API dengan penanganan timeout
try:
    vpn_data = requests.get('http://www.vpngate.net/api/iphone/', timeout=CONNECTION_TIMEOUT).text.replace('\r', '')
    servers = [line.split(',') for line in vpn_data.split('\n') if len(line.split(',')) > 1]
    labels = servers[1]
    labels[0] = labels[0][1:]
    servers = servers[2:]
except requests.exceptions.Timeout:
    print("Request to VPNGate API timed out.")
    exit(1)
except Exception as e:
    print(f"Error fetching VPN servers data: {e}")
    exit(1)

# Menyaring server berdasarkan negara yang dipilih
filtered_servers = []
for country in countries:
    index = 6 if len(country) == 2 else 5
    desired = [s for s in servers if country.lower() in s[index].lower()]
    filtered_servers.extend(desired)

print(f'Found {len(filtered_servers)} servers for countries: {", ".join(countries)}')

# Menyaring server yang mendukung OpenVPN
supported = [s for s in filtered_servers if len(s[-1]) > 0]
print(f"{len(supported)} of these servers support OpenVPN")

# Membuat folder 'ovpn' jika belum ada
os.makedirs('ovpn', exist_ok=True)

# Mendownload dan menyimpan setiap file .ovpn dari server yang sesuai
for server in supported:
    ip = server[1]
    config_base64 = server[-1]
    try:
        ovpn_data = base64.b64decode(config_base64).decode('utf-8')
        filename = f'ovpn/{ip}.ovpn'
        with open(filename, 'w') as f:
            f.write(ovpn_data)
            f.write('\ndata-ciphers AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305:AES-128-CBC')
            f.write('\nscript-security 2\nup /etc/openvpn/update-resolv-conf\ndown /etc/openvpn/update-resolv-conf')
        print(f'Downloaded: {filename}')
    except Exception as e:
        print(f'Failed to download config for server {ip}: {e}')

# Menghapus file konfigurasi spesifik
pattern = re.compile(r"^(219|22122)\..*\.ovpn$")
special_files = [
    '223.134.156.41.ovpn',
    '106.150.249.101.ovpn',
    # Tambahkan file lain sesuai kebutuhan...
]

for file_path in glob.glob('ovpn/*.ovpn'):
    file_name = os.path.basename(file_path)
    if pattern.match(file_name) or file_name in special_files:
        os.remove(file_path)
        print(f"Deleted {file_path} before starting connections.")

# Mengambil daftar file .ovpn untuk koneksi
ovpn_files = glob.glob('ovpn/*.ovpn')
if not ovpn_files:
    print("No .ovpn configuration files found in the 'ovpn' directory.")
    exit(1)

# Fungsi untuk mencatat file konfigurasi yang digunakan
def log_vpn_connection(config_file):
    with open(LOG_FILE, 'a+') as log_file:
        fcntl.flock(log_file, fcntl.LOCK_EX)  # Lock file
        log_file.seek(0)
        used_configs = [line.strip() for line in log_file.readlines()]
        if config_file in used_configs:
            fcntl.flock(log_file, fcntl.LOCK_UN)
            return False
        log_file.write(config_file + '\n')
        fcntl.flock(log_file, fcntl.LOCK_UN)
        return True

# Memilih file .ovpn yang belum digunakan
def select_unused_vpn_config():
    for _ in range(len(ovpn_files)):
        config_path = random.choice(ovpn_files)
        if log_vpn_connection(config_path):
            return config_path
    return None

# Fungsi untuk koneksi VPN
def connect_random_vpn():
    selected_config = select_unused_vpn_config()
    if not selected_config:
        print("All available VPN configurations have been used.")
        return None
    print(f"\nConnecting to VPN server using config file: {selected_config}")
    vpn_process = subprocess.Popen(['openvpn', selected_config], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return vpn_process

# Fungsi untuk mengecek koneksi internet
def check_internet():
    try:
        requests.get("http://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False

# Fungsi untuk mengecek IP publik
def check_current_ip():
    try:
        response = requests.get("http://api.ipify.org", timeout=CHECK_IP_TIMEOUT)
        current_ip = response.text.strip()
        return current_ip != DEFAULT_IP
    except requests.ConnectionError:
        return False

# Loop utama
vpn_process = None

def terminate_vpn():
    global vpn_process
    if vpn_process:
        vpn_process.terminate()
        vpn_process.wait()
        vpn_process = None
        print("VPN connection terminated.")

try:
    while True:
        if vpn_process:
            terminate_vpn()
            print('\nVPN disconnected')
            time.sleep(5)

        vpn_process = connect_random_vpn()
        if not vpn_process:
            break

        retry_count = 0
        while retry_count < MAX_RETRY_LIMIT:
            time.sleep(VPN_CONNECTION_TIMEOUT)
            if vpn_process.poll() is None:
                if check_internet() and check_current_ip():
                    print("Connected to VPN server with new IP.")
                    while True:
                        time.sleep(300)
                        if not check_internet() or not check_current_ip():
                            print("Connection lost or IP mismatch. Reconnecting...")
                            terminate_vpn()
                            break
                    break
                else:
                    print("Connection failed. Retrying...")
            retry_count += 1
            terminate_vpn()
        if retry_count >= MAX_RETRY_LIMIT:
            print("Retry limit reached. Trying a new config.")

except KeyboardInterrupt:
    print("\nTerminating VPN connection...")
    terminate_vpn()
    print("VPN terminated.")
