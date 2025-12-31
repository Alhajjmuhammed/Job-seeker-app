#!/bin/bash
# ============================================
# Worker Connect Database Backup Script
# ============================================
# This script creates backups of the PostgreSQL database
# and media files, with automatic cleanup of old backups.
#
# Usage:
#   ./backup.sh              # Full backup (database + media)
#   ./backup.sh --db-only    # Database only
#   ./backup.sh --media-only # Media only
#   ./backup.sh --restore <backup_file>  # Restore from backup
#
# Cron example (daily at 2 AM):
#   0 2 * * * /path/to/backup.sh >> /var/log/workerconnect/backup.log 2>&1
# ============================================

set -e  # Exit on error

# Configuration (override with environment variables)
BACKUP_DIR="${BACKUP_DIR:-/var/backups/workerconnect}"
APP_DIR="${APP_DIR:-/home/workerconnect/worker-connect}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DATE=$(date +%Y%m%d_%H%M%S)
HOSTNAME=$(hostname -s)

# Database configuration (from environment or .env file)
if [ -f "$APP_DIR/.env" ]; then
    source "$APP_DIR/.env"
fi

DB_NAME="${DB_NAME:-workerconnect}"
DB_USER="${DB_USER:-workerconnect_user}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_PASSWORD="${DB_PASSWORD:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Create backup directory if it doesn't exist
create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_info "Created backup directory: $BACKUP_DIR"
    fi
}

# Backup PostgreSQL database
backup_database() {
    local backup_file="$BACKUP_DIR/${HOSTNAME}_db_${DATE}.sql.gz"
    
    log_info "Starting database backup..."
    
    # Check if pg_dump is available
    if ! command -v pg_dump &> /dev/null; then
        log_error "pg_dump command not found. Please install PostgreSQL client."
        return 1
    fi
    
    # Create backup
    if [ -n "$DB_PASSWORD" ]; then
        PGPASSWORD="$DB_PASSWORD" pg_dump \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --no-owner \
            --no-acl \
            --format=custom \
            | gzip > "$backup_file"
    else
        pg_dump \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --no-owner \
            --no-acl \
            --format=custom \
            | gzip > "$backup_file"
    fi
    
    if [ $? -eq 0 ]; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_info "Database backup completed: $backup_file ($size)"
        echo "$backup_file"
    else
        log_error "Database backup failed!"
        return 1
    fi
}

# Backup media files
backup_media() {
    local media_dir="$APP_DIR/media"
    local backup_file="$BACKUP_DIR/${HOSTNAME}_media_${DATE}.tar.gz"
    
    log_info "Starting media backup..."
    
    if [ ! -d "$media_dir" ]; then
        log_warn "Media directory not found: $media_dir"
        return 0
    fi
    
    # Create tar archive
    tar -czf "$backup_file" -C "$APP_DIR" media/
    
    if [ $? -eq 0 ]; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_info "Media backup completed: $backup_file ($size)"
        echo "$backup_file"
    else
        log_error "Media backup failed!"
        return 1
    fi
}

# Clean up old backups
cleanup_old_backups() {
    log_info "Cleaning up backups older than $RETENTION_DAYS days..."
    
    local count=$(find "$BACKUP_DIR" -name "*.gz" -mtime +$RETENTION_DAYS | wc -l)
    
    if [ $count -gt 0 ]; then
        find "$BACKUP_DIR" -name "*.gz" -mtime +$RETENTION_DAYS -delete
        log_info "Removed $count old backup files"
    else
        log_info "No old backups to clean up"
    fi
}

# Restore database from backup
restore_database() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    log_warn "WARNING: This will overwrite the current database!"
    read -p "Are you sure you want to continue? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        log_info "Restore cancelled."
        return 0
    fi
    
    log_info "Restoring database from: $backup_file"
    
    # Check file extension
    if [[ "$backup_file" == *.gz ]]; then
        if [ -n "$DB_PASSWORD" ]; then
            gunzip -c "$backup_file" | PGPASSWORD="$DB_PASSWORD" pg_restore \
                -h "$DB_HOST" \
                -p "$DB_PORT" \
                -U "$DB_USER" \
                -d "$DB_NAME" \
                --clean \
                --if-exists
        else
            gunzip -c "$backup_file" | pg_restore \
                -h "$DB_HOST" \
                -p "$DB_PORT" \
                -U "$DB_USER" \
                -d "$DB_NAME" \
                --clean \
                --if-exists
        fi
    else
        if [ -n "$DB_PASSWORD" ]; then
            PGPASSWORD="$DB_PASSWORD" pg_restore \
                -h "$DB_HOST" \
                -p "$DB_PORT" \
                -U "$DB_USER" \
                -d "$DB_NAME" \
                --clean \
                --if-exists \
                "$backup_file"
        else
            pg_restore \
                -h "$DB_HOST" \
                -p "$DB_PORT" \
                -U "$DB_USER" \
                -d "$DB_NAME" \
                --clean \
                --if-exists \
                "$backup_file"
        fi
    fi
    
    if [ $? -eq 0 ]; then
        log_info "Database restore completed successfully!"
    else
        log_error "Database restore failed!"
        return 1
    fi
}

# Restore media files
restore_media() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    log_warn "WARNING: This will overwrite current media files!"
    read -p "Are you sure you want to continue? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        log_info "Restore cancelled."
        return 0
    fi
    
    log_info "Restoring media from: $backup_file"
    
    # Create backup of current media
    if [ -d "$APP_DIR/media" ]; then
        mv "$APP_DIR/media" "$APP_DIR/media.old.$(date +%s)"
    fi
    
    # Extract archive
    tar -xzf "$backup_file" -C "$APP_DIR"
    
    if [ $? -eq 0 ]; then
        log_info "Media restore completed successfully!"
        # Remove old media backup
        rm -rf "$APP_DIR/media.old."*
    else
        log_error "Media restore failed!"
        # Restore old media if available
        if [ -d "$APP_DIR/media.old."* ]; then
            mv "$APP_DIR/media.old."* "$APP_DIR/media"
        fi
        return 1
    fi
}

# List available backups
list_backups() {
    log_info "Available backups in $BACKUP_DIR:"
    echo ""
    
    if [ -d "$BACKUP_DIR" ] && [ "$(ls -A $BACKUP_DIR/*.gz 2>/dev/null)" ]; then
        ls -lh "$BACKUP_DIR"/*.gz | awk '{print $9, $5, $6, $7, $8}'
    else
        echo "No backups found."
    fi
}

# Verify backup integrity
verify_backup() {
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    log_info "Verifying backup: $backup_file"
    
    if [[ "$backup_file" == *.tar.gz ]]; then
        if tar -tzf "$backup_file" > /dev/null 2>&1; then
            log_info "Backup verification successful (tar archive is valid)"
            return 0
        else
            log_error "Backup verification failed (tar archive is corrupted)"
            return 1
        fi
    elif [[ "$backup_file" == *.sql.gz ]]; then
        if gunzip -t "$backup_file" > /dev/null 2>&1; then
            log_info "Backup verification successful (gzip archive is valid)"
            return 0
        else
            log_error "Backup verification failed (gzip archive is corrupted)"
            return 1
        fi
    else
        log_warn "Unknown backup format"
        return 1
    fi
}

# Send notification (optional)
send_notification() {
    local status="$1"
    local message="$2"
    
    # Slack notification (if webhook URL is set)
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        local color="good"
        [ "$status" = "error" ] && color="danger"
        
        curl -s -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-type: application/json' \
            -d "{\"attachments\":[{\"color\":\"$color\",\"text\":\"$message\"}]}" \
            > /dev/null
    fi
    
    # Email notification (if mail is configured)
    if [ -n "$NOTIFICATION_EMAIL" ] && command -v mail &> /dev/null; then
        echo "$message" | mail -s "Worker Connect Backup - $status" "$NOTIFICATION_EMAIL"
    fi
}

# Main function
main() {
    local start_time=$(date +%s)
    
    log_info "=========================================="
    log_info "Worker Connect Backup Script"
    log_info "=========================================="
    
    create_backup_dir
    
    case "${1:-}" in
        --db-only)
            backup_database
            ;;
        --media-only)
            backup_media
            ;;
        --restore)
            if [ -z "$2" ]; then
                log_error "Please specify backup file to restore"
                exit 1
            fi
            if [[ "$2" == *"media"* ]]; then
                restore_media "$2"
            else
                restore_database "$2"
            fi
            ;;
        --list)
            list_backups
            ;;
        --verify)
            if [ -z "$2" ]; then
                log_error "Please specify backup file to verify"
                exit 1
            fi
            verify_backup "$2"
            ;;
        --help|-h)
            echo "Usage: $0 [option]"
            echo ""
            echo "Options:"
            echo "  (none)           Full backup (database + media)"
            echo "  --db-only        Backup database only"
            echo "  --media-only     Backup media files only"
            echo "  --restore <file> Restore from backup"
            echo "  --list           List available backups"
            echo "  --verify <file>  Verify backup integrity"
            echo "  --help           Show this help message"
            ;;
        *)
            # Full backup
            backup_database
            backup_media
            cleanup_old_backups
            ;;
    esac
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    log_info "=========================================="
    log_info "Backup completed in ${duration} seconds"
    log_info "=========================================="
    
    send_notification "success" "Worker Connect backup completed successfully in ${duration}s"
}

# Run main function
main "$@"
