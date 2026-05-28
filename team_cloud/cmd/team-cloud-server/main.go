package main

import (
	"context"
	"log"
	"net/http"
	"time"

	"hermes-agent/team_cloud/internal/config"
	"hermes-agent/team_cloud/internal/httpapi"
	"hermes-agent/team_cloud/internal/store/memory"
	"hermes-agent/team_cloud/internal/store/postgres"
)

func main() {
	cfg := config.FromEnv()
	ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer cancel()

	backend := memory.New()
	if cfg.DatabaseURL != "" {
		pg, err := postgres.Open(ctx, cfg.DatabaseURL, cfg.AutoMigrate)
		if err != nil {
			log.Fatalf("open postgres backend: %v", err)
		}
		defer func() {
			if err := pg.Close(); err != nil {
				log.Printf("close postgres backend: %v", err)
			}
		}()
		server, err := httpapi.NewServer(cfg, pg)
		if err != nil {
			log.Fatalf("create server: %v", err)
		}
		server.StartBackupScheduler(context.Background())
		serve(cfg, server)
		return
	}

	server, err := httpapi.NewServer(cfg, backend)
	if err != nil {
		log.Fatalf("create server: %v", err)
	}
	server.StartBackupScheduler(context.Background())
	serve(cfg, server)
}

func serve(cfg config.Config, handler http.Handler) {
	httpServer := &http.Server{
		Addr:              cfg.BindAddr,
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
	}
	log.Printf("starting %s on %s", cfg.ServiceName, cfg.BindAddr)
	if err := httpServer.ListenAndServe(); err != nil {
		log.Fatalf("serve: %v", err)
	}
}
