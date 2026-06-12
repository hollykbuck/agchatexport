# Antigravity Chat Export Viewer

A modern, Go-based tool for viewing and exporting Antigravity chat logs. This project has been migrated from Python to Go to provide a single-file, zero-dependency experience.

## Features

- Single Binary Distribution: Frontend Next.js assets are embedded into the binary using `go:embed`.
- High-Performance Parsing: Native Go implementation for handling Protobuf-serialized chat steps.
- Modern UI: Built-in responsive Web interface powered by Next.js and Tailwind CSS.
- Cross-Platform Support: Binaries available for Linux, Windows, and macOS (amd64/arm64).
- Build Traceability: Support for `-version` flag to view Commit Hash and Build Time.

## Quick Start

### Download

Please visit the [Releases](https://github.com/hollykbuck/agchatexport/releases) page to download the binary for your operating system.

### Running

```bash
# Basic run (default port 7396)
./agchatexport

# Specify database and brain artifact directories
./agchatexport --db-dir ~/.gemini/antigravity-cli/conversations --brain-dir ~/.gemini/antigravity-cli/brain

# Change listening port
./agchatexport --port 8080
```

Once running, access the viewer at `http://localhost:7396` in your browser.

## Development & Build

### Prerequisites

- Go 1.22+
- Node.js 20+ (only for frontend development)
- protoc (only if modifying the protocol)

### Build Steps

1. **Build Frontend**:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

2. **Compile Go Server**:
   ```bash
   go build -o agchatexport main.go
   ```

### Check Build Info

```bash
./agchatexport -version
```

## Project Structure

- `main.go`: Core service logic, including embedded static asset handling and API routing.
- `pb/`: Automatically generated Go Protobuf code.
- `proto/`: Protobuf definitions for Antigravity chat steps.
- `frontend/`: Source code for the Next.js-based frontend.
- `.github/workflows/`: CI/CD pipelines for automated builds and releases.

## License

GPLv3
