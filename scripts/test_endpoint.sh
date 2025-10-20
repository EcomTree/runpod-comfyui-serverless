#!/bin/bash

# ComfyUI RunPod Serverless Test Script
# WARNING: Do not commit real API keys or endpoint IDs to version control!
# Instead, create a copy of this file (e.g. test_endpoint_local.sh) for local testing.

# Configuration - EDIT THESE VALUES
ENDPOINT_ID=""
API_KEY=""
API_URL="https://api.runpod.ai/v2/${ENDPOINT_ID}/runsync"

# Test configuration
TEST_IMAGE_FILENAME="${TEST_IMAGE_FILENAME:-input_image.png}"


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

# Function to validate required configuration
validate_config() {
    if [ -z "$ENDPOINT_ID" ]; then
        print_color $RED "❌ ENDPOINT_ID is not configured!"
        print_color $YELLOW "💡 Please edit this script and set ENDPOINT_ID to your RunPod endpoint ID"
        return 1
    fi

    if [ -z "$API_KEY" ]; then
        print_color $RED "❌ API_KEY is not configured!"
        print_color $YELLOW "💡 Please edit this script and set API_KEY to your RunPod API key"
        return 1
    fi

    if [ -z "$API_URL" ]; then
        print_color $RED "❌ API_URL could not be constructed!"
        return 1
    fi

    return 0
}

# Function to check endpoint health
check_endpoint_health() {
    print_color $BLUE "\n🏥 Checking endpoint health..."

    # Simple connectivity test
    local health_response=$(curl -s -w "%{http_code}" -o /dev/null \
        -X GET \
        -H "Authorization: Bearer $API_KEY" \
        "$API_URL" 2>/dev/null)

    if [ "$health_response" = "401" ]; then
        print_color $YELLOW "⚠️  Authentication issue - check API_KEY"
        return 1
    elif [ "$health_response" = "404" ]; then
        print_color $RED "❌ Endpoint not found - check ENDPOINT_ID"
        return 1
    elif [ "$health_response" = "200" ]; then
        print_color $GREEN "✅ Endpoint is accessible"
        return 0
    else
        print_color $YELLOW "⚠️  Unexpected response: $health_response"
        return 1
    fi
}

# Function to validate workflow response
validate_response() {
    local response="$1"
    local test_name="$2"

    if [ -z "$response" ]; then
        print_color $RED "❌ Empty response from endpoint"
        return 1
    fi

    # Check for error in response
    if echo "$response" | grep -q '"error"'; then
        print_color $RED "❌ Error in response:"
        echo "$response" | jq -r '.error' 2>/dev/null || echo "$response"
        return 1
    fi

    # Check for successful response structure
    if echo "$response" | jq -e '.links and .total_images and .job_id' >/dev/null 2>&1; then
        print_color $GREEN "✅ Response structure is valid"

        local total_images=$(echo "$response" | jq -r '.total_images')
        local storage_type=$(echo "$response" | jq -r '.storage_type')

        print_color $BLUE "📊 Results: $total_images images via $storage_type"

        if [ "$total_images" -gt 0 ]; then
            print_color $GREEN "✅ Test passed: Generated $total_images images"
            return 0
        else
            print_color $YELLOW "⚠️  No images generated"
            return 1
        fi
    else
        print_color $YELLOW "⚠️  Unexpected response structure"
        return 1
    fi
}

# Function to test endpoint
test_endpoint() {
    local test_name="$1"
    local workflow_data="$2"
    local expected_min_images="${3:-1}"

    print_color $BLUE "\n🧪 Test: $test_name"
    print_color $BLUE "===========================================\n"

    # Create request payload
    local payload
    payload=$(cat <<EOF
{
  "input": {
    "workflow": $workflow_data
  }
}
EOF
    )

    print_color $YELLOW "📤 Sending request..."

    # Make the request and capture response with timeout
    local response
    response=$(curl -s --max-time 300 -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $API_KEY" \
        -d "$payload" \
        "$API_URL" 2>&1)

    # Extract response body and status code
    local response_body=$(echo "$response" | sed '$d')
    local status_code=$(echo "$response" | tail -n1)

    print_color $YELLOW "📥 Response Status: $status_code"

    if [ "$status_code" = "200" ]; then
        print_color $GREEN "✅ Request successful!"

        if check_jq >/dev/null 2>&1; then
            echo "$response_body" | jq .
        else
            echo "$response_body"
        fi

        # Validate response structure and content
        if validate_response "$response_body" "$test_name"; then
            local total_images=$(echo "$response_body" | jq -r '.total_images // 0')
            if [ "$total_images" -ge "$expected_min_images" ]; then
                print_color $GREEN "✅ Test passed: Generated $total_images images (expected at least $expected_min_images)"
            else
                print_color $YELLOW "⚠️  Test warning: Generated $total_images images (expected at least $expected_min_images)"
            fi
        else
            print_color $RED "❌ Test failed: Invalid response"
            return 1
        fi
    else
        print_color $RED "❌ Request failed (HTTP $status_code)!"
        print_color $RED "Response: $response_body"

        # Check for common error patterns
        if echo "$response_body" | grep -q "timeout"; then
            print_color $YELLOW "💡 Tip: Workflow may have timed out. Try increasing the timeout or simplifying the workflow."
        elif echo "$response_body" | grep -q "CUDA"; then
            print_color $YELLOW "💡 Tip: Check GPU availability and CUDA version compatibility."
        fi

        return 1
    fi

    return 0
}

# Validate configuration
print_color $GREEN "🚀 Starting ComfyUI Serverless Tests"
print_color $GREEN "=====================================\n"

if ! validate_config; then
    print_color $RED "❌ Configuration validation failed!"
    exit 1
fi

print_color $BLUE "🔗 Endpoint: $ENDPOINT_ID"
print_color $BLUE "🌐 URL: $API_URL\n"

# Check endpoint health
if ! check_endpoint_health; then
    print_color $YELLOW "⚠️  Endpoint health check failed, but continuing with tests..."
    print_color $YELLOW "💡 This might indicate authentication or connectivity issues"
fi

# Test 1: Simple Text-to-Image Workflow (SD 1.5)
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

# Test 2: Image-to-Image Workflow (more complex)
img2img_workflow='{
  "3": {
    "inputs": {
      "seed": 156680208700286,
      "steps": 20,
      "cfg": 8,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 0.75,
      "model": ["4", 0],
      "positive": ["6", 0],
      "negative": ["7", 0],
      "vae": ["4", 2],
      "pixels": ["10", 0]
    },
    "class_type": "KSampler",
    "_meta": {"title": "KSampler"}
  },
  "4": {
    "inputs": {
      "ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {"title": "Load Checkpoint"}
  },
  "6": {
    "inputs": {
      "text": "beautiful landscape, mountains, sunset, highly detailed",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {"title": "CLIP Text Encode (Prompt)"}
  },
  "7": {
    "inputs": {
      "text": "blurry, low quality, artifacts",
      "clip": ["4", 1]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {"title": "CLIP Text Encode (Negative)"}
  },
  "8": {
    "inputs": {
      "samples": ["3", 0],
      "vae": ["4", 2]
    },
    "class_type": "VAEDecode",
    "_meta": {"title": "VAE Decode"}
  },
  "9": {
    "inputs": {
      "filename_prefix": "ComfyUI",
      "images": ["8", 0]
    },
    "class_type": "SaveImage",
    "_meta": {"title": "Save Image"}
  },
  "10": {
    "inputs": {
      "image": "'$TEST_IMAGE_FILENAME'",
      "upload": "image"
    },
    "class_type": "LoadImage",
    "_meta": {"title": "Load Image"}
  }
}'

test_endpoint "Simple Text-to-Image" "$simple_workflow" 1
test_endpoint "Image-to-Image Workflow" "$img2img_workflow" 1

print_color $GREEN "\n🏁 Tests completed!"
print_color $YELLOW "💡 Tips:"
print_color $YELLOW "   • Check the generated images in your configured storage (S3 or Network Volume)"
print_color $YELLOW "   • Image URLs are provided in the 'links' field of the response"
print_color $YELLOW "   • For debugging, check ComfyUI logs in the container"
