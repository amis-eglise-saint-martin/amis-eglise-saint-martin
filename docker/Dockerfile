# Multi-stage build for Église Saint-Martin website
# Stage 1: Build the site with Python
# Stage 2: Serve with nginx

FROM python:3.11-alpine AS builder

WORKDIR /app

# Copy source files and build script
COPY src/ ./src/
COPY build.py ./

# Build arguments for placeholder replacement (required)
ARG DOMAIN
ARG CONTACT_EMAIL
ARG CONTACT_PHONE
ARG FACEBOOK_URL
ARG GITHUB_URL
# Optional arguments
ARG FORMSPREE_ID=
ARG VERSION=dev
# Build mode: "staging" (blocks crawlers) or "production" (allows crawlers)
ARG BUILD_MODE=staging

# Set environment variables for build
ENV DOMAIN=$DOMAIN \
    CONTACT_EMAIL=$CONTACT_EMAIL \
    CONTACT_PHONE=$CONTACT_PHONE \
    FACEBOOK_URL=$FACEBOOK_URL \
    GITHUB_URL=$GITHUB_URL \
    FORMSPREE_ID=$FORMSPREE_ID \
    VERSION=$VERSION

# Build the site (--production flag only if BUILD_MODE=production)
RUN if [ "$BUILD_MODE" = "production" ]; then \
        python build.py --production; \
    else \
        python build.py; \
    fi

# Stage 2: nginx to serve the built site
FROM nginx:alpine

# Install Python for visitor counter script and supercronic for cron
RUN apk add --no-cache python3 curl && \
    SUPERCRONIC_URL="https://github.com/aptible/supercronic/releases/download/v0.2.29/supercronic-linux-amd64" && \
    curl -fsSL "$SUPERCRONIC_URL" -o /usr/local/bin/supercronic && \
    chmod +x /usr/local/bin/supercronic && \
    apk del curl

# Copy built files from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# Copy visitor counter script and crontab
COPY scripts/count_visitors.py /scripts/
COPY docker/crontab /etc/crontab

# Create data directory for visitor count
RUN mkdir -p /data

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port 80
EXPOSE 80

# Health check (use 127.0.0.1 instead of localhost to avoid IPv6 issues in alpine)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/ || exit 1

ENTRYPOINT ["/entrypoint.sh"]
