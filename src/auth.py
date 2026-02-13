import json
import hashlib
import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).parent.parent.resolve()
SYSTEM_DIR = BASE_DIR / "agentic_workspace" / ".system"
USERS_DB_PATH = SYSTEM_DIR / "users.json"

class UserManager:
    def __init__(self, db_path: Path = USERS_DB_PATH):
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        if not self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.db_path, 'w') as f:
                json.dump({}, f)

    def _load_users(self) -> dict:
        try:
            with open(self.db_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_users(self, users: dict):
        with open(self.db_path, 'w') as f:
            json.dump(users, f, indent=4)

    def _hash_password(self, password: str) -> str:
        # Simple SHA-256 hashing. In production, use bcrypt/argon2 with salt.
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username: str, password: str) -> tuple[bool, str]:
        """
        Registers a new user.
        Returns (success, message).
        """
        if not username or not password:
            return False, "Username and password are required."
        
        users = self._load_users()
        
        if username in users:
            return False, "Username already exists."
        
        users[username] = {
            "password_hash": self._hash_password(password),
            "created_at": str(os.path.getctime(self.db_path)) # Just a timestamp placeholder
        }
        
        self._save_users(users)
        return True, "User registered successfully."

    def authenticate_user(self, username: str, password: str) -> bool:
        users = self._load_users()
        
        if username not in users:
            return False
        
        stored_hash = users[username].get("password_hash")
        if stored_hash == self._hash_password(password):
            return True
        
        return False

    def get_user_query_dir(self, username: str) -> Path:
        return BASE_DIR / "agentic_workspace" / "1_queries" / username

# Global instance
user_manager = UserManager()
