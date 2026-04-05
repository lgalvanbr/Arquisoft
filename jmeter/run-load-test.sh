#!/bin/bash

#################################################################
# Arquisoft FinOps - JMeter ASR Load Test Runner
#
# Purpose: Execute the load test with optimized CLI settings
# Usage: bash run-load-test.sh [output_directory] [alb_dns]
#
# Examples:
#   bash run-load-test.sh
#   bash run-load-test.sh ./my-results report-alb-12345.us-east-1.elb.amazonaws.com
#################################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JMX_FILE="${SCRIPT_DIR}/load-test-asr.jmx"
OUTPUT_DIR="${1:-.}"
ALB_DNS="${2:-}"
RESULTS_FILE="${OUTPUT_DIR}/results.jtl"
LOGS_FILE="${OUTPUT_DIR}/jmeter.log"
HTML_REPORT_DIR="${OUTPUT_DIR}/results_html"

# Ensure output directory exists
mkdir -p "${OUTPUT_DIR}"

# Print banner
echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Arquisoft FinOps - ASR Load Test (JMeter)                 ║"
echo "║  5,000 → 12,000 concurrent users | 10-minute ramp-up       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if JMeter is installed
if ! command -v jmeter &> /dev/null; then
    echo -e "${RED}[ERROR] JMeter is not installed or not in PATH${NC}"
    echo ""
    echo "Installation instructions:"
    echo "  • macOS: brew install jmeter"
    echo "  • Linux: sudo apt-get install jmeter"
    echo "  • Windows: Download from https://jmeter.apache.org/download_jmeter.cgi"
    echo ""
    exit 1
fi

# Verify JMeter test file exists
if [ ! -f "${JMX_FILE}" ]; then
    echo -e "${RED}[ERROR] JMeter test file not found: ${JMX_FILE}${NC}"
    exit 1
fi

# Prompt for ALB DNS if not provided
if [ -z "${ALB_DNS}" ]; then
    echo -e "${YELLOW}[INFO] ALB DNS not provided${NC}"
    echo ""
    echo "Please enter your ALB DNS name (e.g., report-alb-123456.us-east-1.elb.amazonaws.com):"
    read -r ALB_DNS
    
    if [ -z "${ALB_DNS}" ]; then
        echo -e "${RED}[ERROR] ALB DNS is required${NC}"
        exit 1
    fi
fi

# Validate ALB DNS format (basic check)
if ! [[ "${ALB_DNS}" =~ ^[a-zA-Z0-9.-]+$ ]]; then
    echo -e "${RED}[ERROR] Invalid ALB DNS format: ${ALB_DNS}${NC}"
    exit 1
fi

echo -e "${GREEN}[INFO] Configuration${NC}"
echo "  Test Plan: ${JMX_FILE}"
echo "  Output Directory: ${OUTPUT_DIR}"
echo "  ALB DNS: ${ALB_DNS}"
echo "  Results File: ${RESULTS_FILE}"
echo "  HTML Report: ${HTML_REPORT_DIR}"
echo ""

# Create a temporary test file with ALB DNS substituted
TEMP_JMX="${OUTPUT_DIR}/load-test-asr-temp.jmx"
cp "${JMX_FILE}" "${TEMP_JMX}"

# Replace ALB DNS placeholders (all occurrences)
sed -i.bak "s/YOUR_ALB_DNS_HERE/${ALB_DNS}/g" "${TEMP_JMX}"
rm -f "${TEMP_JMX}.bak"

echo -e "${BLUE}[START] Running JMeter load test...${NC}"
echo "  Start Time: $(date)"
echo ""

# Run JMeter in CLI mode with HTML report generation
jmeter \
    -n \
    -t "${TEMP_JMX}" \
    -l "${RESULTS_FILE}" \
    -j "${LOGS_FILE}" \
    -e \
    -o "${HTML_REPORT_DIR}" \
    2>&1 | tee -a "${LOGS_FILE}"

# Capture exit code
EXIT_CODE=$?

echo ""
echo -e "${BLUE}[END] Test execution completed${NC}"
echo "  End Time: $(date)"
echo ""

# Clean up temporary file
rm -f "${TEMP_JMX}"

# Check if test was successful
if [ ${EXIT_CODE} -eq 0 ]; then
    echo -e "${GREEN}[SUCCESS] Load test completed successfully${NC}"
    echo ""
    echo -e "${YELLOW}[RESULTS] Generated Files${NC}"
    echo "  JTL Results: ${RESULTS_FILE}"
    echo "  HTML Report: ${HTML_REPORT_DIR}/index.html"
    echo "  Log File: ${LOGS_FILE}"
    echo ""
    
    # Summary statistics
    echo -e "${YELLOW}[SUMMARY] Key Metrics${NC}"
    
    # Parse results using awk/grep (if results file exists)
    if [ -f "${RESULTS_FILE}" ]; then
        TOTAL_SAMPLES=$(grep -c "sample" "${RESULTS_FILE}" || echo "0")
        FAILED_SAMPLES=$(grep 'success="false"' "${RESULTS_FILE}" | wc -l || echo "0")
        SUCCESS_RATE=$(awk "BEGIN {if (${TOTAL_SAMPLES} > 0) printf \"%.2f%%\", (1 - ${FAILED_SAMPLES}/${TOTAL_SAMPLES}) * 100; else print \"N/A\"}")
        
        echo "  Total Samples: ${TOTAL_SAMPLES}"
        echo "  Failed Samples: ${FAILED_SAMPLES}"
        echo "  Success Rate: ${SUCCESS_RATE}"
    fi
    
    echo ""
    echo -e "${GREEN}To view the HTML report:${NC}"
    
    # Detect OS and provide appropriate command
    case "$(uname -s)" in
        Darwin)
            echo "  open ${HTML_REPORT_DIR}/index.html"
            ;;
        Linux)
            echo "  xdg-open ${HTML_REPORT_DIR}/index.html"
            ;;
        MINGW*|MSYS*|CYGWIN*)
            echo "  start ${HTML_REPORT_DIR}/index.html"
            ;;
        *)
            echo "  Open in your browser: file://${HTML_REPORT_DIR}/index.html"
            ;;
    esac
    
    echo ""
    echo -e "${YELLOW}[NEXT STEPS]${NC}"
    echo "  1. Open the HTML report to review detailed metrics"
    echo "  2. Check 'Aggregate Report' for latency percentiles"
    echo "  3. Verify error rate is <5% (for 95% availability)"
    echo "  4. Review 'Response Time Graph' for performance trends"
    echo ""
    echo -e "${GREEN}See README.md for ASR pass/fail criteria and troubleshooting${NC}"
    
else
    echo -e "${RED}[ERROR] Load test failed with exit code ${EXIT_CODE}${NC}"
    echo ""
    echo -e "${YELLOW}[TROUBLESHOOTING]${NC}"
    echo "  • Check log file: ${LOGS_FILE}"
    echo "  • Verify ALB DNS is correct: ${ALB_DNS}"
    echo "  • Confirm Terraform infrastructure is deployed"
    echo "  • Check that report_user exists in Django: python manage.py shell"
    echo ""
    exit ${EXIT_CODE}
fi
