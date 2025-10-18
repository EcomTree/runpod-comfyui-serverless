"""
Workflow processing utilities for ComfyUI
"""
import copy
import random
import time
from typing import Dict, Any, List, Optional

from .config import config


class WorkflowProcessor:
    """Handle workflow processing and seed randomization"""

    def randomize_seeds(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Randomize all seed values in the workflow.

        This function walks through all nodes in the workflow and replaces any 'seed'
        parameters with random values (0 to 2^31-1). This ensures that each workflow
        execution produces different results, even if the same workflow is sent multiple times.

        Args:
            workflow: ComfyUI workflow dictionary

        Returns:
            dict: Modified workflow with randomized seeds (deep copy)
        """
        # Check if seed randomization is disabled via env var
        if not config.get('randomize_seeds', True):
            print("🎲 Seed randomization disabled via RANDOMIZE_SEEDS=false")
            return workflow

        # Create deep copy to avoid in-place modification
        workflow = copy.deepcopy(workflow)
        randomized_count = 0

        def _generate_random_seed():
            """
            Generate a random seed value using getrandbits for better performance.
            
            Returns:
                int: Random seed in range 0 to 2^31-1 (2,147,483,647)
                
            Note:
                Uses 31 bits (not 32) to ensure compatibility with signed 32-bit integers
                used by ComfyUI nodes. This avoids potential overflow issues with nodes
                that expect positive integers within the signed int32 range.
            """
            # getrandbits(31) is used primarily to ensure compatibility with signed 32-bit integers,
            # avoiding overflow issues with nodes expecting positive int32 values. It also has slight
            # performance benefits over randint(0, 2147483647) since it directly generates the required bits.
            return random.getrandbits(31)

        def _randomize_seeds_in_obj(obj, node_id=None, path=""):
            """Recursively traverse and randomize all seed values in nested structures"""
            nonlocal randomized_count

            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if key == "seed" and isinstance(value, (int, float)):
                        # Found a seed parameter - randomize it
                        old_seed = value
                        new_seed = _generate_random_seed()
                        obj[key] = new_seed
                        randomized_count += 1

                        if node_id is not None:
                            print(f"🎲 Node {node_id}: Randomized seed at {current_path}: {old_seed} → {new_seed}")
                        else:
                            print(f"🎲 Randomized seed at {current_path}: {old_seed} → {new_seed}")
                    else:
                        # Recursively process nested structures
                        _randomize_seeds_in_obj(value, node_id=node_id, path=current_path)

            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    current_path = f"{path}[{idx}]" if path else f"[{idx}]"
                    _randomize_seeds_in_obj(item, node_id=node_id, path=current_path)

        # Walk through all nodes in the workflow
        for node_id, node_data in workflow.items():
            if isinstance(node_data, dict) and "inputs" in node_data:
                inputs = node_data["inputs"]
                _randomize_seeds_in_obj(inputs, node_id=node_id, path="inputs")

        if randomized_count > 0:
            print(f"✅ Randomized {randomized_count} seed(s) in workflow")
        else:
            print("ℹ️ No seeds found in workflow to randomize")

        return workflow

    def extract_checkpoint_names(self, object_info: Dict[str, Any]) -> List[str]:
        """Safely extract checkpoint names from ComfyUI object_info response"""
        try:
            # Navigate through the nested structure
            checkpoint_loader = object_info.get("CheckpointLoaderSimple", {})
            input_spec = checkpoint_loader.get("input", {})
            required_spec = input_spec.get("required", {})
            ckpt_name = required_spec.get("ckpt_name", [])

            # Handle nested list format [[model_names], {}]
            if isinstance(ckpt_name, list) and len(ckpt_name) > 0:
                if isinstance(ckpt_name[0], list):
                    # Nested format: extract first list
                    return ckpt_name[0] if len(ckpt_name[0]) > 0 else []
                else:
                    # Simple list format
                    return ckpt_name

            return []
        except (AttributeError, TypeError, KeyError, IndexError) as e:
            print(f"⚠️ Error extracting checkpoint names: {e}")
            return []

    def find_save_nodes(self, workflow: Dict[str, Any]) -> List[str]:
        """Find all SaveImage nodes in the workflow"""
        save_nodes = [k for k, v in workflow.items() if v.get("class_type") == "SaveImage"]
        print(f"💾 SaveImage Nodes found: {len(save_nodes)}")
        return save_nodes

    def count_workflow_nodes(self, workflow: Dict[str, Any]) -> int:
        """Count total nodes in workflow"""
        return len(workflow)

    def get_workflow_node_ids(self, workflow: Dict[str, Any]) -> List[str]:
        """Get all node IDs in workflow"""
        return list(workflow.keys())


# Global workflow processor instance
workflow_processor = WorkflowProcessor()