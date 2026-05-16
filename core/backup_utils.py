import os
import shutil
import zipfile
from datetime import datetime
from django.conf import settings

def get_usb_drives():
    """Detect available USB drives on Windows"""
    import subprocess
    usb_drives = []
    try:
        result = subprocess.run(
            ['wmic', 'logicaldisk', 'where', 'drivetype=2', 'get', 'deviceid'],
            capture_output=True, text=True, shell=True
        )
        lines = result.stdout.strip().split('\n')
        for line in lines[1:]:
            drive = line.strip()
            if drive and len(drive) >= 2:
                usb_drives.append(drive)
    except:
        pass
    return usb_drives

def create_backup(backup_to_usb=False):
    """Create a backup of the database and media files"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_folder = settings.BASE_DIR / 'backups'
    backup_folder.mkdir(exist_ok=True)
    
    # Create backup directory
    backup_dir = backup_folder / f'backup_{timestamp}'
    backup_dir.mkdir(exist_ok=True)
    
    # Backup database
    db_path = settings.BASE_DIR / 'db.sqlite3'
    if db_path.exists():
        shutil.copy2(db_path, backup_dir / 'database.sqlite3')
    
    # Backup media files
    media_path = settings.BASE_DIR / 'media'
    if media_path.exists():
        shutil.copytree(media_path, backup_dir / 'media', dirs_exist_ok=True)
    
    # Create zip file
    zip_path = backup_folder / f'sfms_backup_{timestamp}.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(backup_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, backup_dir.parent)
                zipf.write(file_path, arcname)
    
    # Also copy to USB if requested
    usb_copied = False
    if backup_to_usb:
        usb_drives = get_usb_drives()
        if usb_drives:
            usb_path = f"{usb_drives[0]}/SFMS_Backups"
            os.makedirs(usb_path, exist_ok=True)
            shutil.copy2(zip_path, os.path.join(usb_path, f'sfms_backup_{timestamp}.zip'))
            usb_copied = True
    
    # Clean up temp folder
    shutil.rmtree(backup_dir)
    
    return str(zip_path), usb_copied

def auto_backup_on_exit():
    """Called when user logs out or closes browser"""
    try:
        zip_path, usb_copied = create_backup(backup_to_usb=True)
        return True, zip_path, usb_copied
    except Exception as e:
        return False, str(e), False
