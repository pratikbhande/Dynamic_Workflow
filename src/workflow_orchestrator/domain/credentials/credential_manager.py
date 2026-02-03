"""Credential Management System - Secure storage and retrieval"""
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet
from pydantic import BaseModel
import os
import json
from datetime import datetime


class Credential(BaseModel):
    """Credential model"""
    id: str
    user_id: str
    service_name: str  # "slack", "openai", "pinecone", etc.
    credential_data: Dict[str, str]  # Encrypted
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None


class CredentialManager:
    """
    Manages credentials securely
    
    Features:
    - Encryption at rest
    - Per-user credential storage
    - Credential validation
    - Audit logging
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize credential manager"""
        # Get or generate encryption key
        if encryption_key:
            self.encryption_key = encryption_key.encode()
        else:
            # Try to load from environment
            key = os.getenv("CREDENTIAL_ENCRYPTION_KEY")
            if not key:
                # Generate new key (WARNING: Store this securely!)
                key = Fernet.generate_key()
                print(f"⚠️  Generated new encryption key. Store securely: {key.decode()}")
            self.encryption_key = key if isinstance(key, bytes) else key.encode()
        
        self.cipher = Fernet(self.encryption_key)
    
    def encrypt_value(self, value: str) -> str:
        """Encrypt a credential value"""
        return self.cipher.encrypt(value.encode()).decode()
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt a credential value"""
        return self.cipher.decrypt(encrypted_value.encode()).decode()
    
    async def store_credential(
        self,
        user_id: str,
        service_name: str,
        credential_data: Dict[str, str],
        description: Optional[str] = None
    ) -> str:
        """
        Store credentials for a service
        
        Args:
            user_id: User ID
            service_name: Service identifier (slack, openai, etc.)
            credential_data: Dictionary of credential key-value pairs
            description: Optional description
            
        Returns:
            credential_id
        """
        from ...infrastructure.database.mongodb import get_mongodb
        import uuid
        
        # Encrypt sensitive values
        encrypted_data = {}
        for key, value in credential_data.items():
            encrypted_data[key] = self.encrypt_value(value)
        
        # Create credential record
        credential_id = f"cred_{uuid.uuid4().hex[:12]}"
        credential = {
            "id": credential_id,
            "user_id": user_id,
            "service_name": service_name,
            "credential_data": encrypted_data,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "description": description
        }
        
        # Store in database
        db = await get_mongodb()
        await db.get_collection("credentials").insert_one(credential)
        
        print(f"✅ Stored credentials for {service_name} (user: {user_id})")
        
        return credential_id
    
    async def get_credential(
        self,
        user_id: str,
        service_name: str
    ) -> Optional[Dict[str, str]]:
        """
        Retrieve decrypted credentials
        
        Args:
            user_id: User ID
            service_name: Service identifier
            
        Returns:
            Decrypted credential data or None
        """
        from ...infrastructure.database.mongodb import get_mongodb
        
        db = await get_mongodb()
        credential = await db.get_collection("credentials").find_one({
            "user_id": user_id,
            "service_name": service_name
        })
        
        if not credential:
            return None
        
        # Decrypt values
        decrypted_data = {}
        for key, encrypted_value in credential["credential_data"].items():
            decrypted_data[key] = self.decrypt_value(encrypted_value)
        
        return decrypted_data
    
    async def update_credential(
        self,
        credential_id: str,
        credential_data: Dict[str, str]
    ) -> bool:
        """Update existing credentials"""
        from ...infrastructure.database.mongodb import get_mongodb
        
        # Encrypt new values
        encrypted_data = {}
        for key, value in credential_data.items():
            encrypted_data[key] = self.encrypt_value(value)
        
        db = await get_mongodb()
        result = await db.get_collection("credentials").update_one(
            {"id": credential_id},
            {
                "$set": {
                    "credential_data": encrypted_data,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return result.modified_count > 0
    
    async def delete_credential(
        self,
        user_id: str,
        service_name: str
    ) -> bool:
        """Delete credentials"""
        from ...infrastructure.database.mongodb import get_mongodb
        
        db = await get_mongodb()
        result = await db.get_collection("credentials").delete_one({
            "user_id": user_id,
            "service_name": service_name
        })
        
        return result.deleted_count > 0
    
    async def list_user_credentials(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """List all credentials for a user (without decrypting)"""
        from ...infrastructure.database.mongodb import get_mongodb
        
        db = await get_mongodb()
        cursor = db.get_collection("credentials").find({"user_id": user_id})
        credentials = await cursor.to_list(length=100)
        
        # Return metadata only
        return [
            {
                "id": c["id"],
                "service_name": c["service_name"],
                "description": c.get("description"),
                "created_at": c["created_at"].isoformat(),
                "credential_keys": list(c["credential_data"].keys())
            }
            for c in credentials
        ]
    
    async def validate_credential(
        self,
        user_id: str,
        service_name: str,
        required_keys: List[str]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that credential exists and has required keys
        
        Returns:
            (is_valid, error_message)
        """
        credential = await self.get_credential(user_id, service_name)
        
        if not credential:
            return False, f"No credentials found for {service_name}"
        
        missing_keys = [key for key in required_keys if key not in credential]
        
        if missing_keys:
            return False, f"Missing required credential keys: {missing_keys}"
        
        return True, None


# Global instance
_credential_manager = None


def get_credential_manager() -> CredentialManager:
    """Get global credential manager instance"""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager