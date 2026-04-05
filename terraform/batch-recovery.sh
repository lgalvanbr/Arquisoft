#!/bin/bash
# ==============================================================================
# BATCH RECOVERY SCRIPT: Recover gunicorn on ALL app instances at once
# ==============================================================================
# This script automates the recovery process across multiple instances
# Usage: ./batch-recover.sh <KEY_FILE> <INSTANCE_IPS>
# Example: ./batch-recover.sh ~/arquisoft-key.pem 172.31.69.197 172.31.68.42 172.31.67.89 172.31.66.234
# ==============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
KEY_FILE="${1:-}"
INSTANCE_IPS=("${@:2}")
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECOVERY_SCRIPT="$SCRIPT_DIR/recovery-gunicorn.sh"

echo -e "${BLUE}=========================================="
echo "Batch Gunicorn Recovery Script"
echo "==========================================${NC}"
echo ""

# Validation
if [ -z "$KEY_FILE" ] || [ ${#INSTANCE_IPS[@]} -eq 0 ]; then
    echo -e "${RED}Usage: $0 <KEY_FILE> <IP1> <IP2> <IP3> ...${NC}"
    echo ""
    echo "Example:"
    echo "  $0 ~/arquisoft-key.pem 172.31.69.197 172.31.68.42 172.31.67.89 172.31.66.234"
    echo ""
    echo "Get instance IPs from terraform output:"
    echo "  cd terraform"
    echo "  terraform output app_instances_public_ips"
    exit 1
fi

if [ ! -f "$KEY_FILE" ]; then
    echo -e "${RED}ERROR: Key file not found: $KEY_FILE${NC}"
    exit 1
fi

if [ ! -f "$RECOVERY_SCRIPT" ]; then
    echo -e "${RED}ERROR: Recovery script not found: $RECOVERY_SCRIPT${NC}"
    exit 1
fi

chmod 400 "$KEY_FILE"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Key file: $KEY_FILE"
echo "  Recovery script: $RECOVERY_SCRIPT"
echo "  Number of instances: ${#INSTANCE_IPS[@]}"
echo "  Instance IPs: ${INSTANCE_IPS[@]}"
echo ""

# Function to recover a single instance
recover_instance() {
    local ip=$1
    local index=$2
    local total=$3
    
    echo -e "${BLUE}[${index}/${total}] Recovering instance: $ip${NC}"
    
    # Copy recovery script
    echo "  • Copying recovery script..."
    scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -i "$KEY_FILE" \
        "$RECOVERY_SCRIPT" \
        "ubuntu@$ip:/tmp/recovery-gunicorn.sh" 2>/dev/null || {
        echo -e "${RED}  ✗ Failed to copy script to $ip${NC}"
        return 1
    }
    
    # Execute recovery script
    echo "  • Executing recovery script..."
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -i "$KEY_FILE" \
        "ubuntu@$ip" \
        "bash /tmp/recovery-gunicorn.sh" 2>&1 | sed 's/^/    /' || {
        echo -e "${RED}  ✗ Recovery failed on $ip${NC}"
        return 1
    }
    
    echo -e "${GREEN}  ✓ Instance $ip recovered successfully${NC}"
    echo ""
    return 0
}

# Execute recovery for each instance
SUCCESS_COUNT=0
FAIL_COUNT=0

for i in "${!INSTANCE_IPS[@]}"; do
    ip="${INSTANCE_IPS[$i]}"
    index=$((i + 1))
    total=${#INSTANCE_IPS[@]}
    
    if recover_instance "$ip" "$index" "$total"; then
        ((SUCCESS_COUNT++))
    else
        ((FAIL_COUNT++))
    fi
done

# Summary
echo -e "${BLUE}=========================================="
echo "Recovery Summary"
echo "==========================================${NC}"
echo -e "${GREEN}Successful: $SUCCESS_COUNT${NC}"
echo -e "${RED}Failed: $FAIL_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ All instances recovered successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Wait 30-60 seconds for ALB health checks to update"
    echo "  2. Check ALB target health:"
    echo "     aws elbv2 describe-target-health --target-group-arn <ARN> --region us-east-1"
    echo "  3. Verify application is responding:"
    echo "     curl http://<ALB_DNS>/api/reportes/health"
    exit 0
else
    echo -e "${RED}✗ Some instances failed. See details above.${NC}"
    exit 1
fi
