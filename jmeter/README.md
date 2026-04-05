# Arquisoft FinOps - ASR Load Test (JMeter)

## Overview

This directory contains JMeter configuration files for validating the **Application Service-Level Agreement (ASR)** requirements of the Arquisoft FinOps platform deployed on AWS with Terraform.

### ASR Requirements

| Metric | Target | Description |
|--------|--------|-------------|
| **Concurrent Users** | 5,000 → 12,000 | Ramp-up over 10 minutes |
| **Availability** | ≥95% | Successful request rate |
| **Response Latency** | 2-5 seconds | Average response time (p50) |
| **Error Rate** | <5% | Failed requests should be minimal |
| **Throughput** | ~100-200 req/sec | At full 12K user load |

---

## Files

- **`load-test-asr.jmx`**: Main JMeter test plan (XML format)
- **`run-load-test.sh`**: Shell script for easy test execution
- **`README.md`**: This file

---

## Prerequisites

### 1. Install JMeter

**Windows (Download & Extract):**
```bash
# Download from: https://jmeter.apache.org/download_jmeter.cgi
# Extract to: C:\apache-jmeter-5.5 (or latest version)
# Add to PATH: C:\apache-jmeter-5.5\bin
```

**macOS (Homebrew):**
```bash
brew install jmeter
```

**Linux (apt):**
```bash
sudo apt-get install jmeter
```

### 2. Verify Installation

```bash
jmeter --version
```

Expected output: `Apache JMeter 5.5` (or similar)

### 3. Get ALB DNS Name

After Terraform deployment, retrieve the ALB DNS name from AWS CloudFormation outputs:

```bash
# Option 1: From Terraform state
cd /Arquisoft/terraform
terraform output alb_dns_name

# Option 2: AWS CLI
aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?LoadBalancerName=='report-alb'].DNSName" \
  --output text

# Example output: report-alb-1234567890.us-east-1.elb.amazonaws.com
```

---

## Configuration Steps

### Step 1: Open JMeter GUI

```bash
jmeter -t load-test-asr.jmx
```

### Step 2: Update ALB DNS in Test Plan

1. In JMeter GUI, navigate to **Test Plan → Load Test - Main (5K→12K users, 10min ramp-up) → Loop - Alternate Endpoints**
2. Select **GET /api/reportes/proyecto** sampler
3. Replace `YOUR_ALB_DNS_HERE` with your actual ALB DNS name
   - Example: `report-alb-1438726031.us-east-1.elb.amazonaws.com`
4. **Repeat for GET /api/reportes/consumo** sampler

### Step 3: Verify ALB is Accessible

Test that the ALB is responding to requests:

```bash
curl http://<your-alb-dns>/api/reportes/health
# Expected response: {"status": "healthy", "service": "reportes"}
```

---

## Running the Load Test

### Option 1: GUI Mode (Recommended for First Run)

```bash
jmeter -t load-test-asr.jmx
```

Then click **Start** button to begin the test.

### Option 2: CLI Mode (Headless - Best for Production/Cloud)

```bash
# Run test and generate results file
jmeter -n \
  -t load-test-asr.jmx \
  -l results.jtl \
  -j jmeter.log \
  -e \
  -o results_html

# After test completes, open results_html/index.html in a browser
```

### Option 3: Using the Provided Script (Linux/macOS)

```bash
bash run-load-test.sh
```

---

## Monitoring During Test

### In JMeter GUI:

1. **Summary Report** (Real-time):
   - Shows cumulative stats as users ramp up
   - Watch "Samples" column for total requests sent
   - Watch "Average" and "Min/Max" for latency

2. **Response Time Graph**:
   - Visual representation of latency over time
   - Spike detection for performance issues

3. **View Results Tree** (Debug):
   - Individual request details
   - Request/response headers and body
   - Error messages if any

4. **Aggregate Report** (Detailed):
   - Percentile breakdown (50th, 90th, 95th, 99th)
   - Error count and error percentage

### System Metrics (AWS Console):

Monitor these during the test:

```
EC2 Instances (report-app-lb-a, report-app-lb-b):
  - CPU Utilization: Should not exceed 80% for healthy performance
  - Network In/Out: Monitor for saturation
  - System Status Checks: All should pass

RDS Database (report-db):
  - CPU Utilization: Should be <50% at 12K users
  - Database Connections: Monitor for connection pool exhaustion
  - Read/Write IOPS: Ensure no throttling

Application Load Balancer (report-alb):
  - Target Group Health: All targets should be "Healthy"
  - HTTP 4XX/5XX: Track error responses
  - Request Count: Should scale linearly with users
  - Latency (ALB perspective): Compare with app response time
```

---

## Test Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  Time: 0-600s (10 minutes)                                      │
│  Main Thread Group (Ramp-up: 5,000 → 12,000 users)              │
│  Users added: ~20 users/sec (12,000 / 600 = 20 users/sec)       │
│                                                                 │
│  Each user loop (continuous until test ends):                   │
│    1. GET /api/reportes/proyecto (public endpoint)              │
│    2. GET /api/reportes/consumo (public endpoint)               │
│    3. Repeat                                                    │
│                                                                 │
│  Load profile: Linear ramp-up, no hold time                     │
│  Test ends at t=600s when all users have been spawned           │
└─────────────────────────────────────────────────────────────────┘
```

## API Architecture

The test targets **public endpoints** (no authentication required):

- **GET /api/reportes/proyecto**: Public endpoint, returns project reports
- **GET /api/reportes/consumo**: Public endpoint, returns cloud consumption data

Both endpoints are available without JWT token authentication, allowing the load test to focus purely on API performance and scalability testing.

---

## Interpreting Results

### ASR Pass/Fail Criteria

After test completion, check these metrics in **Aggregate Report**:

#### 1. Availability (Target: ≥95%)

```
Formula: (Successful Requests / Total Requests) × 100

JMeter Location: Aggregate Report → "Error %" column
  - Error % should be ≤5% (meaning ≥95% success rate)

Example:
  Total Samples: 1,000,000
  Failed: 40,000
  Error %: 4%
  ✓ PASS (95% availability achieved)
```

#### 2. Response Latency (Target: 2-5 seconds)

```
JMeter Location: Aggregate Report

Key columns:
  - Average (ms): Should be 2,000-5,000 ms
  - 90th pct (ms): Should be <6,000 ms
  - 95th pct (ms): Should be <7,000 ms
  - Max (ms): Track for extreme outliers

Example:
  Average: 3,245 ms ✓ PASS (within 2-5s)
  90th pct: 5,123 ms ✓ PASS
  95th pct: 6,789 ms ⚠ WARNING (above 5s)
```

#### 3. Throughput (Expected: 100-200 req/sec at peak)

```
JMeter Location: Aggregate Report → "Throughput" column (req/sec)

Calculation:
  At 12,000 concurrent users:
  If average request takes 3 seconds (3,000 ms):
  Throughput = 12,000 users / 3 seconds = 4,000 req/sec
  
  This varies based on:
  - Response time of endpoints
  - Number of concurrent requests per user
  - ALB capacity and routing

Example (Healthy):
  Throughput: 150 req/sec at peak
  ✓ PASS (within expected range)
```

#### 4. Error Analysis

```
JMeter Location: View Results Tree (expand failed requests)

Common errors to investigate:
  - 401 Unauthorized: JWT token extraction failed or expired
  - 502 Bad Gateway: ALB → app connection issue
  - 503 Service Unavailable: Target health check failing
  - 504 Gateway Timeout: Request exceeded 30s timeout
  - Connection Refused: App instance down
  - Read Timed Out: App processing too slowly

Resolution steps:
  1. Check app logs: ssh to instance, tail /var/log/django-app.log
  2. Check ALB target health: AWS Console → Load Balancers
  3. Check RDS: AWS Console → RDS → Databases
  4. Review Response Time Graph for performance degradation patterns
```

---

## Expected Performance Profile

During the ramp-up phase:

```
Time (min) | Users | Avg Latency | Errors | Status
-----------|-------|-------------|--------|--------
0-1        | 0-1K  | 1,500 ms    | 0.5%   | ✓ PASS
1-2        | 1-2K  | 2,000 ms    | 0.5%   | ✓ PASS
2-3        | 2-3K  | 2,200 ms    | 0.5%   | ✓ PASS
3-4        | 3-4K  | 2,500 ms    | 0.5%   | ✓ PASS
4-5        | 4-5K  | 2,800 ms    | 0.5%   | ✓ PASS
5-6        | 5-6K  | 3,000 ms    | 0.5%   | ✓ PASS
6-7        | 6-7K  | 3,200 ms    | 1%     | ✓ PASS
7-8        | 7-8K  | 3,400 ms    | 1%     | ✓ PASS
8-9        | 8-9K  | 3,600 ms    | 1%     | ✓ PASS
9-10       | 9-12K | 3,800 ms    | 2%     | ⚠ CAUTION (approaching limit)
```

If latency shoots above 10 seconds or errors exceed 10%, the system is reaching capacity.

---

## Troubleshooting

### Problem: "Unable to resolve host: YOUR_ALB_DNS_HERE"

**Solution**: You forgot to update the ALB DNS in the test plan. Replace all occurrences with your actual ALB DNS name.

### Problem: "401 Unauthorized - Invalid Token"

**Solution**: 
1. Verify `report_user` exists in Django: `python manage.py shell`
2. Check JWT token expiry (default: 1 hour) - test may be too long if >1 hour
3. Verify token extraction regex in JSON Extractor matches response format

### Problem: "502 Bad Gateway"

**Solution**:
1. Check ALB target health: AWS Console → Load Balancers → Targets
2. SSH into app instance and check Django status: `sudo systemctl status django-app`
3. Tail logs: `sudo tail -f /var/log/django-app.log`

### Problem: "504 Gateway Timeout"

**Solution**:
1. Increase request timeout (currently 30s): Edit JMeter test plan
2. Check if DB query is slow: Enable Django query logging
3. Consider scaling up EC2 instance type (t2.micro → t2.small)

### Problem: High latency but no errors

**Solution**:
1. System is handling load but slowly
2. Reduce concurrent users OR scale infrastructure:
   - Add more EC2 instances to Target Group
   - Upgrade instance type (t2.micro → t3.medium)
   - Optimize Django views (add caching, database indexing)

---

## Post-Test Analysis

### Generate HTML Report (CLI Mode)

```bash
jmeter -g results.jtl -o results_html
# Open results_html/index.html in browser for detailed charts
```

### Export Data to CSV for Analysis

```bash
# Using JMeter built-in aggregation
jmeter -g results.jtl \
  --reportonly \
  -o results_analysis \
  -Jjmeter.reportgenerator.agg_type=avg

# CSV output available in results_analysis/
```

### Key Metrics to Document

After each test run, document:

```
Test Run: [Date/Time]
Environment: AWS (Terraform-deployed)
ALB: [DNS name]
Load Profile: 5,000 → 12,000 users, 10-minute ramp-up
Duration: [Total time]

Results:
  - Total Requests: [N]
  - Successful: [N] ([%])
  - Failed: [N] ([%])
  - Average Latency: [Xms]
  - 95th Percentile: [Xms]
  - Throughput (peak): [X req/sec]
  - ASR Status: [PASS/FAIL]

Issues/Notes:
  - [Any observations about performance]
  - [Any errors encountered]
  - [Recommendations for improvement]
```

---

## Scaling Infrastructure Based on Results

If you don't meet ASR targets, consider these adjustments:

### If error rate >5%:

1. **Increase EC2 instances**: Add more servers to the Target Group
   ```bash
   # In deployment.tf, increase EC2 instance count
   # Or manually add instances and register with Target Group
   ```

2. **Upgrade instance type**: t2.micro → t2.small or t3.medium
   ```bash
   # Stop instances, change instance type, restart
   ```

3. **Enable RDS auto-scaling**: For database performance
   ```bash
   # AWS Console → RDS → Enable Performance Insights
   ```

### If latency >5 seconds:

1. **Add Django caching**: Redis/Memcached
2. **Optimize database queries**: Add indexes, reduce N+1 queries
3. **Enable ALB request compression**: Gzip responses

### If throughput is too low:

1. **Increase ALB connection limits** (default: 1,000)
2. **Tune connection pooling** in Django (currently: default)
3. **Consider upgrading ALB to NLB** if UDP/extreme throughput needed

---

## References

- [JMeter Documentation](https://jmeter.apache.org/usermanual/)
- [Arquisoft Django Settings](../finops_platform/settings.py)
- [Terraform Deployment](../terraform/README.md)
- [AWS Load Balancer Documentation](https://docs.aws.amazon.com/elasticloadbalancing/)

---

## Support

For issues or questions:

1. Check JMeter logs: `jmeter.log` in the test directory
2. Review Django application logs on EC2 instances
3. Monitor AWS CloudWatch metrics during test
4. Report bugs: https://github.com/anomalyco/opencode

---

**Last Updated**: April 5, 2026
**Arquisoft FinOps Team**
