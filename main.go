package main

import (
	"database/sql"
	"embed"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"io/fs"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/hollykbuck/agchatexport/pb"
	"github.com/rs/cors"
	"google.golang.org/protobuf/proto"
	_ "modernc.org/sqlite"
)

//go:embed all:frontend/out
var embeddedFrontend embed.FS

type Config struct {
	DBDir    string
	BrainDir string
	Host     string
	Port     int
}

var config Config

func main() {
	home, _ := os.UserHomeDir()
	flag.StringVar(&config.DBDir, "db-dir", filepath.Join(home, ".gemini/antigravity-cli/conversations"), "Directory for conversation databases")
	flag.StringVar(&config.BrainDir, "brain-dir", filepath.Join(home, ".gemini/antigravity-cli/brain"), "Directory for brain artifacts")
	flag.StringVar(&config.Host, "host", "localhost", "Host to bind")
	flag.IntVar(&config.Port, "port", 7396, "Port to bind")
	flag.Parse()

	mux := http.NewServeMux()

	mux.HandleFunc("GET /api/chats", apiListChats)
	mux.HandleFunc("GET /api/chat/{db_name}", apiChatDetail)
	mux.HandleFunc("GET /api/brain/{db_uuid}/{path...}", apiViewArtifact)

	// Serve static files
	frontendFS, err := fs.Sub(embeddedFrontend, "frontend/out")
	if err != nil {
		log.Fatal(err)
	}
	fileServer := http.FileServer(http.FS(frontendFS))

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		// Only handle GET for static files
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		path := strings.TrimPrefix(r.URL.Path, "/")
		if path == "" {
			path = "index.html"
		} else if path == "chat" {
			path = "chat.html"
		}

		// Try to serve the file from embedded FS
		_, err := fs.Stat(frontendFS, path)
		if err == nil {
			fileServer.ServeHTTP(w, r)
			return
		}

		// If not found and it's not a file-like path (no extension), serve index.html
		if !strings.Contains(filepath.Base(path), ".") {
			r.URL.Path = "/index.html"
			fileServer.ServeHTTP(w, r)
			return
		}

		// Otherwise, let FileServer return 404
		fileServer.ServeHTTP(w, r)
	})

	handler := cors.AllowAll().Handler(mux)

	addr := fmt.Sprintf("%s:%d", config.Host, config.Port)
	fmt.Printf("Server starting at http://%s\n", addr)
	log.Fatal(http.ListenAndServe(addr, handler))
}

func apiListChats(w http.ResponseWriter, r *http.Request) {
	files, err := filepath.Glob(filepath.Join(config.DBDir, "*.db"))
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	dbNames := make([]string, 0, len(files))
	for _, f := range files {
		dbNames = append(dbNames, filepath.Base(f))
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string][]string{"chats": dbNames})
}

func apiChatDetail(w http.ResponseWriter, r *http.Request) {
	dbName := r.PathValue("db_name")
	dbUUID := strings.TrimSuffix(dbName, ".db")
	dbPath := filepath.Join(config.DBDir, dbName)

	if _, err := os.Stat(dbPath); os.IsNotExist(err) {
		http.Error(w, "Database not found", http.StatusNotFound)
		return
	}

	messages, err := getMessages(dbPath)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	artifacts := getArtifacts(config.BrainDir, dbUUID)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"db_name":   dbName,
		"db_uuid":   dbUUID,
		"messages":  messages,
		"artifacts": artifacts,
	})
}

func getMessages(dbPath string) ([]map[string]interface{}, error) {
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, err
	}
	defer db.Close()

	rows, err := db.Query("SELECT idx, step_type, step_payload FROM steps ORDER BY idx")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var messages []map[string]interface{}
	for rows.Next() {
		var idx int
		var stepType int
		var payload []byte
		if err := rows.Scan(&idx, &stepType, &payload); err != nil {
			continue
		}

		step := &pb.Step{}
		if err := proto.Unmarshal(payload, step); err != nil {
			continue
		}

		msg := map[string]interface{}{
			"idx":  idx,
			"type": stepType,
		}

		if step.UserMessage != nil {
			content := step.UserMessage.TextContent_2
			if content == "" && step.UserMessage.NestedContent_3 != nil {
				content = step.UserMessage.NestedContent_3.RawText
			}
			msg["role"] = "USER"
			msg["content"] = content
			messages = append(messages, msg)
		} else if step.AssistantMessage != nil {
			msg["role"] = "ASSISTANT"
			content := step.AssistantMessage.TextContent
			if step.AssistantMessage.ToolDirective != nil {
				td := step.AssistantMessage.ToolDirective
				toolCall := map[string]interface{}{
					"tool_name": td.ToolName,
				}
				var args interface{}
				if err := json.Unmarshal([]byte(td.ArgsJson), &args); err != nil {
					toolCall["args_raw"] = td.ArgsJson
				} else {
					toolCall["args"] = args
				}
				msg["tool_call"] = toolCall
			}
			msg["content"] = content
			messages = append(messages, msg)
		} else if step.ToolOutput != nil {
			msg["role"] = "OBSERVATION"
			msg["content"] = step.ToolOutput.Content
			msg["key"] = step.ToolOutput.Key
			messages = append(messages, msg)
		}
	}

	return messages, nil
}

func getArtifacts(brainDir, dbUUID string) []string {
	brainPath := filepath.Join(brainDir, dbUUID)
	var artifacts []string
	filepath.Walk(brainPath, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() {
			return nil
		}
		rel, err := filepath.Rel(brainPath, path)
		if err == nil {
			artifacts = append(artifacts, rel)
		}
		return nil
	})
	return artifacts
}

func apiViewArtifact(w http.ResponseWriter, r *http.Request) {
	dbUUID := r.PathValue("db_uuid")
	path := r.PathValue("path")
	fullPath := filepath.Join(config.BrainDir, dbUUID, path)

	if info, err := os.Stat(fullPath); os.IsNotExist(err) || info.IsDir() {
		http.Error(w, "Artifact not found", http.StatusNotFound)
		return
	}

	f, err := os.Open(fullPath)
	if err != nil {
		http.Error(w, fmt.Sprintf("Error reading artifact: %v", err), http.StatusInternalServerError)
		return
	}
	defer f.Close()

	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	io.Copy(w, f)
}
