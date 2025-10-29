# ComfyUI Custom Nodes Guide

This guide covers the custom nodes installation system and the 6 essential nodes included in the deployment.

## Table of Contents

- [Overview](#overview)
- [Included Custom Nodes](#included-custom-nodes)
- [Installation](#installation)
- [Management](#management)
- [Configuration](#configuration)

## Overview

The deployment includes an automated custom node installation system that manages 6 essential nodes:

1. **ComfyUI-Manager** - Essential management tool
2. **ComfyUI-Impact-Pack** - Advanced image processing
3. **rgthree-comfy** - Workflow enhancements
4. **ComfyUI-Advanced-ControlNet** - Extended ControlNet support
5. **ComfyUI-VideoHelperSuite** - Video processing
6. **ComfyUI_LoadImageFromHttpURL** - HTTP image loading

## Included Custom Nodes

### 1. ComfyUI-Manager

**Repository:** [ltdrdata/ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager)

**Features:**
- Model management interface
- Custom node installation
- Update management
- Snapshot/restore functionality

**Use Cases:**
- Install additional nodes via UI
- Download models easily
- Manage ComfyUI versions

**Priority:** 1 (Highest)

### 2. ComfyUI-Impact-Pack

**Repository:** [ltdrdata/ComfyUI-Impact-Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack)

**Features:**
- Advanced image segmentation
- Detail refinement
- Face/hand detection and enhancement
- Mask operations

**Key Nodes:**
- `Detailer` - Enhance specific regions
- `SAMDetector` - Segment Anything Model
- `BBoxDetector` - Bounding box detection
- `MaskBlur` - Advanced mask operations

**Use Cases:**
- Face enhancement
- Detail refinement
- Selective inpainting
- Object segmentation

**Priority:** 2

### 3. rgthree-comfy

**Repository:** [rgthree/rgthree-comfy](https://github.com/rgthree/rgthree-comfy)

**Features:**
- Workflow organization tools
- Better node connections
- Context switchers
- Power prompts

**Key Nodes:**
- `Context` - Pass multiple connections
- `Power Prompt` - Enhanced prompt editing
- `Seed` - Better seed management
- `Display Any` - Debug any value

**Use Cases:**
- Organize complex workflows
- Reduce connection clutter
- A/B testing
- Debugging

**Priority:** 3

### 4. ComfyUI-Advanced-ControlNet

**Repository:** [Kosinkadink/ComfyUI-Advanced-ControlNet](https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet)

**Features:**
- Advanced ControlNet scheduling
- Multi-ControlNet support
- Timestep keyframes
- Weight scheduling

**Key Nodes:**
- `Apply Advanced ControlNet` - Enhanced control
- `TimestepKeyframe` - Time-based control
- `ControlNetLoaderAdvanced` - Advanced loading

**Use Cases:**
- Complex pose control
- Animation with ControlNet
- Multi-condition generation
- Fine-grained control

**Priority:** 4

### 5. ComfyUI-VideoHelperSuite

**Repository:** [Kosinkadink/ComfyUI-VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite)

**Features:**
- Video loading and saving
- Frame extraction
- Video combination
- Audio handling

**Key Nodes:**
- `Load Video` - Import video files
- `Save Video` - Export with audio
- `Video Info` - Get video metadata
- `Combine Images to Video` - Create animations

**Use Cases:**
- Video-to-video workflows
- Animation creation
- Frame interpolation
- Video processing

**Priority:** 5

### 6. ComfyUI_LoadImageFromHttpURL

**Repository:** [jerrywap/ComfyUI_LoadImageFromHttpURL](https://github.com/jerrywap/ComfyUI_LoadImageFromHttpURL)

**Features:**
- Load images from URLs
- HTTP/HTTPS support
- Direct integration

**Key Nodes:**
- `Load Image From URL` - Fetch remote images

**Use Cases:**
- API workflows
- Remote image processing
- Dynamic image sources
- Serverless applications

**Priority:** 6

## Installation

### Automated Installation (Recommended)

All nodes are automatically installed during Docker build:

```dockerfile
# Dockerfile includes
ARG INSTALL_CUSTOM_NODES=true
RUN /workspace/scripts/install_custom_nodes.sh install
```

### Manual Installation

```bash
# Install all configured nodes
/workspace/scripts/install_custom_nodes.sh install

# Install specific node
cd /workspace/ComfyUI/custom_nodes
git clone <node_repository_url>
cd <node_name>
pip install -r requirements.txt  # if exists
```

### Selective Installation

Edit `/workspace/configs/custom_nodes.json`:

```json
{
  "custom_nodes": [
    {
      "name": "ComfyUI-Manager",
      "repo": "https://github.com/ltdrdata/ComfyUI-Manager.git",
      "required": true,  // Set to false to skip
      "install_requirements": true,
      "priority": 1
    }
  ]
}
```

## Management

### List Installed Nodes

```bash
/workspace/scripts/install_custom_nodes.sh list
```

**Output:**
```
✓ ComfyUI-Manager
✓ ComfyUI-Impact-Pack
✓ rgthree-comfy
✓ ComfyUI-Advanced-ControlNet
✓ ComfyUI-VideoHelperSuite
✓ ComfyUI_LoadImageFromHttpURL
Total custom nodes: 6
```

### Update All Nodes

```bash
/workspace/scripts/install_custom_nodes.sh update
```

### Verify Installation

```bash
/workspace/scripts/install_custom_nodes.sh verify
```

### Remove a Node

```bash
/workspace/scripts/install_custom_nodes.sh remove <node_name>
```

**Example:**
```bash
/workspace/scripts/install_custom_nodes.sh remove ComfyUI-Manager
```

## Configuration

### Custom Nodes Config

Location: `/workspace/configs/custom_nodes.json`

```json
{
  "custom_nodes": [
    {
      "name": "ComfyUI-Manager",
      "repo": "https://github.com/ltdrdata/ComfyUI-Manager.git",
      "description": "Essential management tool",
      "priority": 1,
      "required": true,
      "install_requirements": true,
      "dependencies": [],
      "tags": ["management", "essential"]
    }
  ],
  "installation_notes": {
    "order": "Nodes installed in priority order",
    "dependencies": "Some nodes depend on others",
    "requirements": "Python requirements auto-processed",
    "restart": "May need ComfyUI restart"
  },
  "configuration": {
    "parallel_install": false,
    "retry_on_failure": true,
    "max_retries": 3,
    "skip_on_error": false,
    "verify_after_install": true
  }
}
```

### Adding New Nodes

1. Edit `/workspace/configs/custom_nodes.json`
2. Add node configuration:

```json
{
  "name": "YourCustomNode",
  "repo": "https://github.com/user/node.git",
  "description": "Your description",
  "priority": 7,
  "required": false,
  "install_requirements": true,
  "tags": ["your-tags"]
}
```

3. Run installer:

```bash
/workspace/scripts/install_custom_nodes.sh install
```

### Environment Variables

```bash
# Custom nodes directory
COMFYUI_PATH=/workspace/ComfyUI

# Config file location
CONFIG_FILE=/workspace/configs/custom_nodes.json

# Skip errors and continue
SKIP_ON_ERROR=false
```

## Troubleshooting

### Installation Failures

**Check logs:**
```bash
cat /workspace/logs/custom_nodes_install.log
```

**Common issues:**
- Missing dependencies
- Network timeouts
- Git authentication

**Solutions:**
```bash
# Retry installation
/workspace/scripts/install_custom_nodes.sh install

# Skip failed node and continue
SKIP_ON_ERROR=true /workspace/scripts/install_custom_nodes.sh install
```

### Node Not Appearing in ComfyUI

**Verify installation:**
```bash
ls /workspace/ComfyUI/custom_nodes/
```

**Check for __init__.py:**
```bash
ls /workspace/ComfyUI/custom_nodes/YourNode/__init__.py
```

**Restart ComfyUI:**
```bash
# Will restart automatically on next request in serverless
```

### Dependency Conflicts

**Check requirements:**
```bash
cat /workspace/ComfyUI/custom_nodes/YourNode/requirements.txt
```

**Manual install:**
```bash
pip install -r /workspace/ComfyUI/custom_nodes/YourNode/requirements.txt
```

## Best Practices

### 1. Priority Order

Nodes install in priority order (1 = highest):
- Essential dependencies first
- Core functionality next
- Optional features last

### 2. Required vs Optional

Mark critical nodes as `required: true`:
- Installation fails if required node fails
- Optional nodes can be skipped

### 3. Dependencies

Specify dependencies explicitly:
```json
{
  "name": "ComfyUI-Impact-Pack",
  "dependencies": ["ComfyUI-Manager"]
}
```

### 4. Regular Updates

Update nodes periodically:
```bash
# Monthly or as needed
/workspace/scripts/install_custom_nodes.sh update
```

### 5. Testing

Test new nodes before production:
```bash
# Install in development
/workspace/scripts/install_custom_nodes.sh install

# Verify functionality
/workspace/scripts/install_custom_nodes.sh verify
```

## Development

### Creating Node Config

```bash
# Template for new node
{
  "name": "NodeName",
  "repo": "https://github.com/user/repo.git",
  "description": "What it does",
  "priority": 10,
  "required": false,
  "install_requirements": true,
  "dependencies": [],
  "tags": ["category"]
}
```

### Testing Installation

```bash
# Dry run (check only)
/workspace/scripts/install_custom_nodes.sh verify

# Install single node
cd /workspace/ComfyUI/custom_nodes
git clone <repo>
pip install -r <node>/requirements.txt
```

## Advanced Usage

### Parallel Installation

```json
{
  "configuration": {
    "parallel_install": true  // Faster but riskier
  }
}
```

### Custom Install Scripts

Some nodes have custom installers:
- `install.py` - Python install script
- `install.sh` - Bash install script

The installer runs these automatically.

### Version Pinning

```bash
# Clone specific version
cd /workspace/ComfyUI/custom_nodes/NodeName
git checkout v1.2.3
```

## References

- [ComfyUI Custom Nodes List](https://github.com/ltdrdata/ComfyUI-Manager/blob/main/custom_node_list.json)
- [ComfyUI Documentation](https://github.com/comfyanonymous/ComfyUI)
- [Node Development Guide](https://github.com/comfyanonymous/ComfyUI/blob/master/NODES.md)

## Support

For node-specific issues:
1. Check node's GitHub repository
2. Review installation logs
3. Verify dependencies
4. Test with minimal workflow
