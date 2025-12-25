import requests
import json
import os

def download_ofac_sdn():
    """Download OFAC SDN list and convert to searchable format"""
    
    url = "https://www.treasury.gov/ofac/downloads/sdn.csv"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        names = []
        lines = response.text.split("\n")
        
        for line in lines[1:]:
            if line.strip():
                parts = line.split(",")
                if len(parts) > 1:
                    name = parts[1].strip().strip('"')
                    if name and len(name) > 2:
                        names.append(name.upper())
        
        with open("data/ofac_sdn_names.json", "w") as f:
            json.dump({"names": names, "count": len(names)}, f)
        
        print(f"✅ Downloaded {len(names)} names from OFAC SDN list")
        return names
        
    except Exception as e:
        print(f"❌ Failed to download OFAC list: {e}")
        return []

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    download_ofac_sdn()
