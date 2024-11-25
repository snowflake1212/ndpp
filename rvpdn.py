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
HAPUS_IPS = ["111.217.191.8", "133.175.28.203"]  # IP default yang harus dicek setiap 5 menit
LOG_FILE = '/home/python/log_ovpn.txt'  # Lokasi file log di host

# Mengecek argumen input untuk menerima lebih dari satu negara
if len(sys.argv) < 2:
    print('usage: ' + sys.argv[0] + ' [country name | country code]...')
    exit(1)
countries = sys.argv[1:]

# Mengambil data dari VPNGate API dengan mekanisme retry
MAX_RETRY_API = 3  # Jumlah maksimal percobaan ke API VPNGate
retry_count = 0

while retry_count < MAX_RETRY_API:
    try:
        print(f"Fetching VPNGate API data (Attempt {retry_count + 1}/{MAX_RETRY_API})...")
        vpn_data = requests.get('http://www.vpngate.net/api/iphone/', timeout=CONNECTION_TIMEOUT).text.replace('\r', '')
        servers = [line.split(',') for line in vpn_data.split('\n') if len(line.split(',')) > 1]
        labels = servers[1]
        labels[0] = labels[0][1:]
        servers = servers[2:]
        print("Successfully fetched VPNGate API data.")
        break  # Jika berhasil, keluar dari loop
    except requests.exceptions.Timeout:
        retry_count += 1
        print(f"Timeout occurred while fetching VPNGate API data. Retrying {retry_count}/{MAX_RETRY_API}...")
    except Exception as e:
        print(f"Error fetching VPN servers data: {e}")
        exit(1)

if retry_count == MAX_RETRY_API:
    print("Failed to fetch VPNGate API data after multiple retries.")
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
pattern = re.compile(r"^(21999|22122)\..*\.ovpn$")
special_files = [
    '223.134.156.41.ovpn',
    '106.150.249.101.ovpn',
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

# Fungsi untuk mencatat file konfigurasi yang berhasil digunakan
def log_successful_vpn_connection(config_file):
    with open(LOG_FILE, 'a+') as log_file:
        fcntl.flock(log_file, fcntl.LOCK_EX)
        log_file.write(config_file + '\n')
        fcntl.flock(log_file, fcntl.LOCK_UN)

# Fungsi untuk memonitor output OpenVPN
def monitor_openvpn_output(vpn_process, timeout=5):
    start_time = time.time()
    while time.time() - start_time < timeout:
        output_line = vpn_process.stdout.readline()
        output_line = output_line.strip()
        if "Initialization Sequence Completed" in output_line:
            print("OpenVPN successfully connected.")
            return True
        elif vpn_process.poll() is not None:
            print("OpenVPN process terminated unexpectedly.")
            return False
    print("Initialization Sequence did not complete in time.")
    return False

# Fungsi untuk koneksi VPN dengan timeout dan pencatatan log setelah berhasil
def connect_random_vpn_with_timeout():
    selected_config = random.choice(ovpn_files)
    print(f"\nConnecting to VPN server using config file: {selected_config}")
    vpn_process = subprocess.Popen(
        ['openvpn', '--config', selected_config],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True
    )
    if monitor_openvpn_output(vpn_process, timeout=5):
        log_successful_vpn_connection(selected_config)
        return vpn_process
    else:
        vpn_process.terminate()
        vpn_process.wait()
        print("Restarting connection with a new configuration.")
        return None

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
        return current_ip not in HAPUS_IPS
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

        vpn_process = connect_random_vpn_with_timeout()
        if not vpn_process:
            print("Failed to connect. Trying a new configuration.")
            continue

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
