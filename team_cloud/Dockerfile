FROM node:22-alpine AS dashboard-build

WORKDIR /src/dashboard
COPY dashboard/package.json dashboard/package-lock.json ./
RUN npm ci
COPY dashboard/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM golang:1.24-alpine AS build

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/team-cloud-server ./cmd/team-cloud-server

FROM gcr.io/distroless/static-debian12:nonroot

COPY --from=build /out/team-cloud-server /usr/local/bin/team-cloud-server
COPY --from=dashboard-build /src/dashboard/out /usr/share/team-cloud-go/dashboard

ENV TEAM_CLOUD_DASHBOARD_ENABLED=true
ENV TEAM_CLOUD_DASHBOARD_DIR=/usr/share/team-cloud-go/dashboard

USER nonroot:nonroot
EXPOSE 8780
ENTRYPOINT ["/usr/local/bin/team-cloud-server"]
