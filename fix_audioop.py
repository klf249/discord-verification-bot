# fix_audioop.py
import sys
import subprocess

print("🔧 Installation du module audioop pour Python 3.13...")

# Installer audioop via pip
subprocess.check_call([sys.executable, "-m", "pip", "install", "audioop-lts"])

print("✅ Module audioop installé avec succès!")