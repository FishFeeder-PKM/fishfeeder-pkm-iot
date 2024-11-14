import os
import shutil
import subprocess

def install_requirements():
    """Install dependencies from requirements.txt."""
    try:
        subprocess.check_call([os.sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("Successfully installed requirements.")
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while installing requirements: {e}")
        exit(1)

def copy_env_file():
    """Copy .env.example to .env if .env does not already exist."""
    if os.path.exists('.env'):
        print(".env already exists. Skipping copy of .env.example.")
    elif os.path.exists('.env.example'):
        shutil.copy('.env.example', '.env')
        print("Successfully copied .env.example to .env.")
    else:
        print(".env.example file not found. Skipping .env copy.")
        exit(1)

if __name__ == "__main__":
    install_requirements()
    copy_env_file()
