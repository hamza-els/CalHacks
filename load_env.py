"""Simple script to load environment variables from .env file"""
import os
from pathlib import Path

def load_env_file(env_file='.env'):
    """Load environment variables from .env file"""
    env_path = Path(env_file)
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print(f"Loaded environment variables from {env_file}")
    else:
        print(f"No {env_file} file found")

if __name__ == "__main__":
    load_env_file()
    print(f"ANTHROPIC_API_KEY is set: {'ANTHROPIC_API_KEY' in os.environ}")

