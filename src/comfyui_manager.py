"""
ComfyUI Manager Module

This module is kept for backward compatibility but is not used in the Coding Background Agent.
The original ComfyUI functionality has been replaced with code analysis and development tools.
"""

from typing import Dict, Any, List
from pathlib import Path

class ComfyUIManager:
    """
    ComfyUI Manager - Legacy module for backward compatibility.
    
    This class is maintained for compatibility but is not actively used
    in the Coding Background Agent configuration.
    """
    
    def __init__(self):
        self.logger = None
    
    def start_server_if_needed(self) -> bool:
        """Legacy method - always returns True for compatibility."""
        return True
    
    def run_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy method - returns empty result for compatibility."""
        return {}
    
    def find_generated_images(self, result: Dict[str, Any], start_time: float) -> List[Path]:
        """Legacy method - returns empty list for compatibility."""
        return []
    
    def cleanup_temp_files(self, image_paths: List[Path]) -> None:
        """Legacy method - no-op for compatibility."""
        pass


# Global instance for backward compatibility
comfyui_manager = ComfyUIManager()