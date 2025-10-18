#!/bin/bash

# WARNING: Do not commit real API keys or endpoint IDs to version control!
# Instead, create a copy of this file (e.g. test_endpoint_local.sh) for local testing.

# Configuration
ENDPOINT_ID=""
API_KEY=""
API_URL=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    printf "${1}%s${NC}\n" "$2"
}

# Function to check if jq is installed
check_jq() {
    if ! command -v jq &> /dev/null; then
        print_color $RED "❌ jq is not installed. Please install jq for better JSON output."
        print_color $YELLOW "🔧 Installation: brew install jq (macOS) or apt-get install jq (Ubuntu)"
        return 1
    fi
    return 0
}

# Function to test endpoint
test_endpoint() {
    local test_name="$1"
    local workflow_data="$2"
    
    print_color $BLUE "\n🧪 Test: $test_name"
    print_color $BLUE "===========================================\n"
    
    # Create request payload
    local payload=$(cat <<EOF
{
  "input": {
    "workflow": $workflow_data
  }
}
EOF
    )
    
    print_color $YELLOW "📤 Sending request..."
    
    # Make the request and capture response
    local response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $API_KEY" \
        -d "$payload" \
        "$API_URL")
    
    # Extract response body and status code
    local response_body=$(echo "$response" | sed '$d')
    local status_code=$(echo "$response" | tail -n1)
    
    print_color $YELLOW "📥 Response Status: $status_code"
    
    if [ "$status_code" = "200" ]; then
        print_color $GREEN "✅ Request successful!"
        
        if check_jq; then
            echo "$response_body" | jq .
        else
            echo "$response_body"
        fi
    else
        print_color $RED "❌ Request failed!"
        print_color $RED "Response: $response_body"
    fi
}

# Check if API_KEY and ENDPOINT_ID are set
if [ "$API_KEY" = "YOUR_RUNPOD_API_KEY" ] || [ "$ENDPOINT_ID" = "YOUR_ENDPOINT_ID" ]; then
    print_color $RED "❌ Please set API_KEY and ENDPOINT_ID in this script!"
    print_color $YELLOW "🔧 Edit the variables at the beginning of the script:"
    print_color $YELLOW "   ENDPOINT_ID=\"your-endpoint-id\""
    print_color $YELLOW "   API_KEY=\"your-api-key\""
    exit 1
fi

print_color $GREEN "🚀 Starting ComfyUI Serverless Tests"
print_color $GREEN "=====================================\n"
print_color $BLUE "🔗 Endpoint: $ENDPOINT_ID"
print_color $BLUE "🌐 URL: $API_URL\n"

# Test 1: Simple Text-to-Image Workflow
simple_workflow='{
  "3": {
    "inputs": {
      "seed": 156680208700286,
      "steps": 20,
      "cfg": 8,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1,
      "model": [
        "4",
        0
      ],
      "positive": [
        "6",
        0
      ],
      "negative": [
        "7",
        0
      ],
      "latent_image": [
        "5",
        0
      ]
    },
    "class_type": "KSampler",
    "_meta": {
      "title": "KSampler"
    }
  },
  "4": {
    "inputs": {
      "ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint"
    }
  },
  "5": {
    "inputs": {
      "width": 512,
      "height": 512,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "Empty Latent Image"
    }
  },
  "6": {
    "inputs": {
      "text": "beautiful scenery nature glass bottle landscape, , purple galaxy bottle,",
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "7": {
    "inputs": {
      "text": "text, watermark",
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "8": {
    "inputs": {
      "samples": [
        "3",
        0
      ],
      "vae": [
        "4",
        2
      ]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE Decode"
    }
  },
  "9": {
    "inputs": {
      "filename_prefix": "ComfyUI",
      "images": [
        "8",
        0
      ]
    },
    "class_type": "SaveImage",
    "_meta": {
      "title": "Save Image"
    }
  }
}'

test_endpoint "Simple Text-to-Image" "$simple_workflow"

print_color $GREEN "\n🏁 Tests completed!"
print_color $YELLOW "💡 Tip: Check the generated images in your Volume Output Directory"
