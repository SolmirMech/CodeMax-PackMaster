# core/packaging/packaging_manager.py
from core.packaging.packaging_data_manager import PackagingDataManager


class PackagingManager:
    """Тонкая обёртка над PackagingDataManager"""
    
    def __init__(self, config_manager, coordinator=None):
        self.config = config_manager
        self.coordinator = coordinator
        self.data_manager = PackagingDataManager(config_manager, coordinator)
    
    def get_recent_entries(self, limit=10):
        return self.data_manager.get_recent(limit)
    
    def search_entries(self, **filters):
        return self.data_manager.search(filters)
    
    def update_cell(self, entry_id, column, value):
        return self.data_manager.update_entry(entry_id, column, value)
    
    def add_entry(self, data):
        return self.data_manager.add_entry(data)
    
    def delete_entry(self, entry_id):
        return self.data_manager.delete_entry(entry_id)