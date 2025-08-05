#!/bin/bash
# Cron Setup Script for Swiss News Scraper
# Sets up automated scraping every 4 hours using cron
# Issue: https://github.com/devpouya/swissnews/issues/6

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RUNNER_SCRIPT="$PROJECT_ROOT/backend/scraper/runner.py"
LOG_DIR="/var/log/swissnews"
CRON_LOG_FILE="$LOG_DIR/cron.log"

# Default values
PYTHON_PATH=""
VIRTUAL_ENV=""
ENVIRONMENT="production"
DRY_RUN=false
REMOVE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Show usage information
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Setup cron job for Swiss News Scraper (runs every 4 hours)

Options:
    --python-path PATH      Path to Python executable (auto-detected if not specified)
    --virtual-env PATH      Path to virtual environment (optional)
    --environment ENV       Environment: production, staging, development (default: production)
    --log-dir DIR          Directory for log files (default: /var/log/swissnews)
    --dry-run              Show what would be done without making changes
    --remove               Remove existing cron job
    --help                 Show this help message

Examples:
    $0                                          # Auto-detect Python and setup
    $0 --virtual-env /path/to/venv             # Use specific virtual environment
    $0 --python-path /usr/bin/python3.9       # Use specific Python
    $0 --dry-run                               # Preview changes
    $0 --remove                                # Remove cron job

Environment Variables:
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD  # Database configuration
    LOG_LEVEL                                         # Logging level (default: INFO)

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --python-path)
                PYTHON_PATH="$2"
                shift 2
                ;;
            --virtual-env)
                VIRTUAL_ENV="$2"
                shift 2
                ;;
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --log-dir)
                LOG_DIR="$2"
                CRON_LOG_FILE="$LOG_DIR/cron.log"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --remove)
                REMOVE=true
                shift
                ;;
            --help)
                show_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

# Auto-detect Python path
detect_python() {
    if [[ -n "$VIRTUAL_ENV" ]]; then
        PYTHON_PATH="$VIRTUAL_ENV/bin/python"
    elif [[ -z "$PYTHON_PATH" ]]; then
        # Try to find Python 3
        for py in python3.11 python3.10 python3.9 python3.8 python3 python; do
            if command -v "$py" >/dev/null 2>&1; then
                PYTHON_PATH="$(command -v "$py")"
                break
            fi
        done
    fi
    
    if [[ -z "$PYTHON_PATH" ]]; then
        print_error "Could not find Python executable. Please specify --python-path"
        exit 1
    fi
    
    if [[ ! -x "$PYTHON_PATH" ]]; then
        print_error "Python executable not found or not executable: $PYTHON_PATH"
        exit 1
    fi
    
    print_info "Using Python: $PYTHON_PATH"
}

# Verify runner script exists and is executable
verify_runner_script() {
    if [[ ! -f "$RUNNER_SCRIPT" ]]; then
        print_error "Runner script not found: $RUNNER_SCRIPT"
        exit 1
    fi
    
    if [[ ! -x "$RUNNER_SCRIPT" ]]; then
        print_warning "Making runner script executable: $RUNNER_SCRIPT"
        if [[ "$DRY_RUN" == "false" ]]; then
            chmod +x "$RUNNER_SCRIPT"
        fi
    fi
    
    print_info "Runner script: $RUNNER_SCRIPT"
}

# Create log directory
setup_log_directory() {
    if [[ ! -d "$LOG_DIR" ]]; then
        print_info "Creating log directory: $LOG_DIR"
        if [[ "$DRY_RUN" == "false" ]]; then
            sudo mkdir -p "$LOG_DIR"
            sudo chown "$(whoami):$(whoami)" "$LOG_DIR"
        fi
    fi
    
    print_info "Log directory: $LOG_DIR"
    print_info "Cron log file: $CRON_LOG_FILE"
}

# Generate cron command
generate_cron_command() {
    local env_vars=""
    
    # Add environment variables
    [[ -n "${DB_HOST:-}" ]] && env_vars+="DB_HOST=\"$DB_HOST\" "
    [[ -n "${DB_PORT:-}" ]] && env_vars+="DB_PORT=\"$DB_PORT\" "
    [[ -n "${DB_NAME:-}" ]] && env_vars+="DB_NAME=\"$DB_NAME\" "
    [[ -n "${DB_USER:-}" ]] && env_vars+="DB_USER=\"$DB_USER\" "
    [[ -n "${DB_PASSWORD:-}" ]] && env_vars+="DB_PASSWORD=\"$DB_PASSWORD\" "
    [[ -n "${LOG_LEVEL:-}" ]] && env_vars+="LOG_LEVEL=\"$LOG_LEVEL\" "
    
    # Add Python path to environment
    env_vars+="PATH=\"$(dirname "$PYTHON_PATH"):\$PATH\" "
    
    # Construct the command
    local cmd="$env_vars\"$PYTHON_PATH\" \"$RUNNER_SCRIPT\" --mode=cron --log-file=\"$CRON_LOG_FILE\""
    
    echo "$cmd"
}

# Get current cron jobs
get_current_cron() {
    crontab -l 2>/dev/null || true
}

# Remove existing cron job
remove_cron_job() {
    local current_cron
    current_cron=$(get_current_cron)
    
    if echo "$current_cron" | grep -q "swissnews.*runner.py"; then
        print_info "Removing existing Swiss News Scraper cron job..."
        
        if [[ "$DRY_RUN" == "false" ]]; then
            # Remove lines containing our scraper
            echo "$current_cron" | grep -v "swissnews.*runner.py" | crontab -
        fi
        
        print_info "Cron job removed successfully"
    else
        print_info "No existing Swiss News Scraper cron job found"
    fi
}

# Install cron job
install_cron_job() {
    local current_cron
    local cron_command
    local cron_schedule="0 */4 * * *"  # Every 4 hours at minute 0
    
    current_cron=$(get_current_cron)
    cron_command=$(generate_cron_command)
    
    # Check if job already exists
    if echo "$current_cron" | grep -q "swissnews.*runner.py"; then
        print_warning "Swiss News Scraper cron job already exists. Removing old version..."
        remove_cron_job
        current_cron=$(get_current_cron)
    fi
    
    # Add the new cron job
    local new_cron_entry="$cron_schedule $cron_command >> \"$CRON_LOG_FILE\" 2>&1"
    
    print_info "Installing cron job:"
    print_info "Schedule: Every 4 hours (at 0, 4, 8, 12, 16, 20 o'clock)"
    print_info "Command: $cron_command"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        {
            echo "$current_cron"
            echo "# Swiss News Scraper - runs every 4 hours"
            echo "$new_cron_entry"
        } | crontab -
        
        print_info "Cron job installed successfully"
    else
        print_info "[DRY RUN] Would install the following cron entry:"
        echo "$new_cron_entry"
    fi
}

# Test the setup
test_setup() {
    print_info "Testing runner script..."
    
    local test_cmd="\"$PYTHON_PATH\" \"$RUNNER_SCRIPT\" --status --json-output"
    
    if [[ "$DRY_RUN" == "false" ]]; then
        if eval "$test_cmd" >/dev/null; then
            print_info "Runner script test: PASSED"
        else
            print_warning "Runner script test: FAILED (this may be expected if database is not set up)"
        fi
    else
        print_info "[DRY RUN] Would test with: $test_cmd"
    fi
}

# Main function
main() {
    print_info "Swiss News Scraper Cron Setup"
    print_info "=============================="
    
    # Parse arguments
    parse_args "$@"
    
    if [[ "$REMOVE" == "true" ]]; then
        remove_cron_job
        exit 0
    fi
    
    # Setup steps
    detect_python
    verify_runner_script
    setup_log_directory
    install_cron_job
    test_setup
    
    print_info ""
    print_info "Setup completed successfully!"
    print_info ""
    print_info "The scraper will now run automatically every 4 hours."
    print_info "Logs will be written to: $CRON_LOG_FILE"
    print_info ""
    print_info "To check status manually:"
    print_info "  $PYTHON_PATH $RUNNER_SCRIPT --status"
    print_info ""
    print_info "To remove the cron job:"
    print_info "  $0 --remove"
}

# Run main function with all arguments
main "$@"