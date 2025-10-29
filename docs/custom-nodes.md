# Custom Nodes

This project ships with an automated installer for a curated set of essential ComfyUI custom nodes.

## Installed by default

- ComfyUI-Manager (`https://github.com/ltdrdata/ComfyUI-Manager`)
- ComfyUI-Impact-Pack (`https://github.com/ltdrdata/ComfyUI-Impact-Pack`)
- rgthree-comfy (`https://github.com/rgthree/rgthree-comfy`)
- ComfyUI-Advanced-ControlNet (`https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet`)
- ComfyUI-VideoHelperSuite (`https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite`)
- ComfyUI_LoadImageFromHttpURL (`https://github.com/jerrywap/ComfyUI_LoadImageFromHttpURL`)

The list is defined in `configs/custom_nodes.json` and can be customized.

## How it works

During the Docker build, the installer clones each repository into `ComfyUI/custom_nodes` and installs Python requirements if present. It is safe to re-run; existing folders are updated with `git pull`.

```bash
bash scripts/install_custom_nodes.sh configs/custom_nodes.json
```

## Customize the list

Edit `configs/custom_nodes.json` and add or remove entries:

```json
{
  "install_root": "/workspace/ComfyUI/custom_nodes",
  "nodes": [
    { "name": "MyNode", "repo": "https://github.com/user/MyNode.git", "install_requirements": true }
  ]
}
```

You can also run the installer at runtime to add nodes without rebuilding the image.
