package api

import (
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/sandalichandrasekara/rootlens/pkg/metrics"
)

// getAllowedOrigins returns the list of allowed CORS origins
func getAllowedOrigins() []string {
	origins := []string{
		"http://localhost:3000",
		"http://localhost:5173",
		"http://127.0.0.1:3000",
		"https://rootlens.xyz",
		"https://www.rootlens.xyz",
	}

	if extra := os.Getenv("ALLOWED_ORIGIN"); extra != "" {
		for _, o := range strings.Split(extra, ",") {
			o = strings.TrimSpace(o)
			if o != "" {
				origins = append(origins, o)
			}
		}
	}

	return origins
}

// isOriginAllowed checks if the request origin is in the whitelist
func isOriginAllowed(origin string, allowedOrigins []string) bool {
	for _, allowed := range allowedOrigins {
		if origin == allowed {
			return true
		}
	}
	return false
}

// CORSMiddleware adds CORS headers to allow frontend access from whitelisted origins
func CORSMiddleware(next http.Handler) http.Handler {
	allowedOrigins := getAllowedOrigins()

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		origin := r.Header.Get("Origin")

		if isOriginAllowed(origin, allowedOrigins) {
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
			w.Header().Set("Access-Control-Max-Age", "3600")
		}

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}

// JSONContentType sets JSON content type header
func JSONContentType(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		next(w, r)
	}
}

// EnforceJSONContentType rejects POST/PUT/PATCH requests that don't declare
// Content-Type: application/json. This is the standard CSRF defence for JSON
// APIs — browsers cannot send application/json cross-origin without a CORS
// preflight, which our CORSMiddleware already blocks for unknown origins.
func EnforceJSONContentType(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodPost, http.MethodPut, http.MethodPatch:
			ct := r.Header.Get("Content-Type")
			if ct != "application/json" {
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusUnsupportedMediaType)
				w.Write([]byte(`{"error":"Content-Type must be application/json"}`)) //nolint:errcheck
				return
			}
		}
		next(w, r)
	}
}

// InstrumentRequests records per-endpoint request count and latency to Prometheus
func InstrumentRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rw := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rw, r)
		duration := time.Since(start).Seconds()
		metrics.APIRequestsTotal.WithLabelValues(r.URL.Path, r.Method, strconv.Itoa(rw.status)).Inc()
		metrics.APIRequestDuration.WithLabelValues(r.URL.Path).Observe(duration)
	})
}

// statusRecorder wraps ResponseWriter to capture the written status code
type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}

// SecurityHeaders adds basic security headers to every response
func SecurityHeaders(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("X-Frame-Options", "DENY")
		w.Header().Set("X-XSS-Protection", "1; mode=block")
		w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
		next.ServeHTTP(w, r)
	})
}
