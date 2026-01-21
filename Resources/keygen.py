import sys
import os
from cryptography.fernet import Fernet

ID = sys.argv[1]
os.makedirs(os.path.join("ID", ID))
ID_DIR = os.path.join("ID", ID)
k = Fernet.generate_key()
with open(os.path.join(ID_DIR, "infos.txt"), "wb") as f:
	f.write(k)
