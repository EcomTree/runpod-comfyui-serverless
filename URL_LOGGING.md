# URL Logging Configuration

## Problem
By default, presigned S3 URLs contain sensitive authentication tokens in their query parameters. For security reasons, these query parameters are removed from logs, showing only the base URL path with a note: `[presigned - query params redacted for security]`.

Example of sanitized log output:
```
Generated URL: https://bucket.r2.cloudflarestorage.com/path/to/file.mp4 [presigned - query params redacted for security]
```

## Solution: Full URL Logging

To log the **complete presigned URLs** (including authentication tokens), set the following environment variable:

```bash
DEBUG_S3_URLS=true
```

### Important Security Warning ⚠️

**Full presigned URLs contain sensitive authentication tokens!**
- Only enable `DEBUG_S3_URLS=true` in development/debugging
- Never share logs with full presigned URLs
- Never commit logs with full presigned URLs to version control
- In production, keep this setting disabled (default: `false`)

## Alternative: Use Public URLs

If you don't want presigned URLs at all, you can configure your S3/R2 bucket for public access and set:

```bash
S3_PUBLIC_URL=https://your-public-cdn.com/bucket-name
```

With this configuration:
- No authentication tokens in URLs
- URLs are always fully visible in logs
- You must configure your bucket for public read access
- Consider using a CDN like Cloudflare for better performance

## Log Output

After these changes, the handler will now log all output URLs:

```
✅ Handler successful! 1 images processed
☁️ Images uploaded to S3: your-bucket-name
📦 Images saved to volume: ['/path/to/volume/output/file.mp4']
🔗 URL 1/1: https://full-url-to-your-file.mp4
```

## Configuration Summary

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DEBUG_S3_URLS` | `false` | Log full presigned URLs with authentication tokens |
| `S3_PUBLIC_URL` | (empty) | Use public URLs instead of presigned URLs |

## Example Configuration

### Development (Full URLs)
```bash
DEBUG_S3_URLS=true
```

### Production (Secure, with presigned URLs)
```bash
DEBUG_S3_URLS=false
```

### Production (Public CDN)
```bash
S3_PUBLIC_URL=https://cdn.example.com/media
DEBUG_S3_URLS=false
```

