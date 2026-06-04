from app.storage.service import StorageService, SupabaseStorageService


def get_storage_service() -> StorageService:
    return SupabaseStorageService.from_settings()
