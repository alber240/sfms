import json
import requests
from pathlib import Path

def check_for_updates():
    """Check if newer version is available"""
    # Read current version
    version_file = Path(__file__).parent.parent / 'version.json'
    if version_file.exists():
        with open(version_file, 'r') as f:
            current = json.load(f)
        current_version = current.get('version', '1.0')
    else:
        current_version = '1.0'
    
    # Check online for latest version
    try:
        # You would host this file on your server
        response = requests.get('https://your-server.com/sfms/version.json', timeout=5)
        if response.status_code == 200:
            latest = response.json()
            latest_version = latest.get('version', '1.0')
            
            if latest_version != current_version:
                return {
                    'update_available': True,
                    'current_version': current_version,
                    'latest_version': latest_version,
                    'release_notes': latest.get('changes', [])
                }
    except:
        pass
    
    return {'update_available': False}