# Implementation Summary - Arquisoft FinOps ASR Load Test

## ✅ Completed Tasks

### 1. JMeter Directory Structure
- **Location**: `/Arquisoft/jmeter/`
- **Files Created**: 4 files totaling ~43 KB

### 2. JMeter Test Plan (load-test-asr.jmx)
- **18 KB XML configuration**
- **Setup Phase**: 
  - 1 thread (single user)
  - Executes `POST /api/auth/login` to obtain JWT token
  - JSON extractor captures `access_token` from response
  
- **Main Load Test Phase**:
  - ThreadGroup: 12,000 concurrent users
  - Ramp-up: 600 seconds (10 minutes)
  - ~20 users spawned per second
  - No hold time (test ends when ramp-up completes)
  
- **Request Pattern**:
  - Interleave controller alternates between:
    - `GET /api/reportes/proyecto` (with JWT Bearer header)
    - `GET /api/reportes/consumo` (with JWT Bearer header)
  - Each request includes:
    - `Authorization: Bearer ${ACCESS_TOKEN}`
    - `Content-Type: application/json`
    - 30-second timeout
  
- **Results Collectors**:
  - Summary Report (real-time stats)
  - Response Time Graph (latency visualization)
  - View Results Tree (detailed debugging)
  - Aggregate Report (percentile analysis)
  - Backend Listener (metrics export)

### 3. README.md (13 KB)
Comprehensive documentation including:

- **Overview**: ASR requirements (95% availability, 2-5s latency, 5K→12K users)
- **Prerequisites**: JMeter installation instructions for Windows/macOS/Linux
- **Configuration Steps**: How to update ALB DNS and verify credentials
- **Running the Test**: GUI mode, CLI mode (headless), and script execution options
- **Monitoring**: What metrics to watch during test execution
- **Test Execution Flow**: Diagram showing setup and main phases
- **Interpreting Results**:
  - Availability calculation (error % ≤ 5%)
  - Latency metrics (average, 90th, 95th percentiles)
  - Throughput analysis
  - Error code troubleshooting
- **Expected Performance Profile**: Table showing metrics at each minute of ramp-up
- **Troubleshooting**: Solutions for common issues (DNS resolution, auth failures, 502 errors)
- **Post-Test Analysis**: HTML report generation and metrics documentation
- **Scaling Infrastructure**: Recommendations based on test results

### 4. QUICKSTART.md (6 KB)
Quick reference guide with:
- 3-step startup procedure
- Summary of test configuration
- ASR success criteria checklist
- Key metrics to monitor (during test and in AWS Console)
- Common troubleshooting scenarios
- Performance tuning recommendations
- File locations and support links

### 5. run-load-test.sh (6 KB)
Bash script for automated execution:
- **Functionality**:
  - Validates JMeter installation
  - Prompts for ALB DNS (if not provided as argument)
  - Creates output directory for results
  - Substitutes ALB DNS into test plan
  - Executes JMeter in headless mode
  - Generates HTML reports
  - Provides colored output with status messages
  
- **Usage**:
  ```bash
  bash run-load-test.sh                          # Interactive
  bash run-load-test.sh ./results alb-dns-name  # Non-interactive
  ```
  
- **Output Files**:
  - `results.jtl`: Raw test results (XML)
  - `jmeter.log`: Execution logs
  - `results_html/index.html`: Interactive report

## 📊 Test Specification

### Load Profile

```
Phase 1: Setup (t=0s)
  └─ 1 user authenticates and extracts JWT token
  
Phase 2: Ramp-up (t=0-600s)
  └─ 5,000 → 12,000 users at ~20 users/sec
     Each user alternates:
     • GET /api/reportes/proyecto (JWT required)
     • GET /api/reportes/consumo (JWT required)
     • Loop continues until test end (t=600s)
```

### Authentication Flow

```
1. Setup user calls: POST /api/auth/login
   • Username: report_user
   • Password: isis2503
   • Response: { "access_token": "eyJ0...", "refresh_token": "..." }

2. JSON Extractor: $.access_token → ${ACCESS_TOKEN}

3. Main users call endpoints with:
   • Header: Authorization: Bearer ${ACCESS_TOKEN}
   • Token valid for 1 hour
```

### Expected Metrics at Full Load (12,000 users)

| Metric | Target | Notes |
|--------|--------|-------|
| **Availability** | ≥95% | Success rate = 1 - (failed / total) |
| **P50 Latency** | 2-5s | 50th percentile response time |
| **P95 Latency** | <7s | 95th percentile response time |
| **Error Rate** | <5% | 401, 502, 503, 504 errors |
| **Throughput** | 100-200 req/sec | At peak load (varies by app latency) |

## 🔧 Integration with Existing Infrastructure

### Django Application (finops_platform/)

The test validates these endpoints:
- **POST /api/auth/login** (autenticacion/views.py)
  - No auth required
  - Returns JWT tokens
  
- **GET /api/reportes/proyecto** (reportes/views.py)
  - Requires `@permission_classes([IsAuthenticated])`
  - Uses JWT Bearer authentication
  - Returns project-level reporting data
  
- **GET /api/reportes/consumo** (reportes/views.py)
  - Requires `@permission_classes([IsAuthenticated])`
  - Uses JWT Bearer authentication
  - Returns consumption/usage data

- **GET /api/reportes/health** (ALB health check endpoint)
  - No auth required
  - Used by ALB Target Group (30-second intervals)

### AWS Infrastructure (terraform/)

The test targets:
- **Application Load Balancer** (report-alb)
  - DNS name: hardcoded in JMeter test
  - Port: 80 (HTTP)
  - Routes to 2 EC2 instances via Round-Robin

- **EC2 Instances** (report-app-lb-a, report-app-lb-b)
  - Instance type: t2.micro
  - Runs Django application on port 8080
  - Health checks every 30 seconds

- **RDS Database** (report-db)
  - Engine: PostgreSQL
  - Used by Django ORM for reports data
  - Connection limit: ~100 connections (t3.micro)

## 📝 User Instructions

### Before Running Test

1. **Deploy Terraform infrastructure** (if not already deployed):
   ```bash
   cd terraform/
   terraform init
   terraform apply
   ```

2. **Verify Django application is running**:
   ```bash
   # SSH to app instance
   ssh -i your-key.pem ec2-user@<app-ip>
   sudo systemctl status django-app
   ```

3. **Confirm report_user exists**:
   ```bash
   python manage.py shell
   >>> from django.contrib.auth import get_user_model
   >>> User = get_user_model()
   >>> User.objects.filter(username='report_user').exists()
   True
   ```

### Running the Test

**Option 1: GUI (Interactive)**
```bash
jmeter -t jmeter/load-test-asr.jmx
# In JMeter GUI:
# 1. Find all "YOUR_ALB_DNS_HERE" and replace with actual ALB DNS
# 2. Click "Start" button
# 3. Monitor Summary Report, Response Time Graph, etc.
```

**Option 2: CLI (Headless)**
```bash
bash jmeter/run-load-test.sh ./results report-alb-123456.us-east-1.elb.amazonaws.com
# Generates results_html/index.html with charts and metrics
```

### Analyzing Results

1. **Check ASR Compliance**:
   - Open `Aggregate Report` tab in JMeter (or HTML report)
   - Verify: Error % < 5% → ✓ Availability ≥95%
   - Verify: Average < 5000ms → ✓ Latency requirement met
   - Verify: Max < 20000ms → ✓ No extreme outliers

2. **Review Performance Trends**:
   - Check Response Time Graph for spikes
   - Compare p50, p95, p99 percentiles
   - Identify where latency starts to increase

3. **Monitor AWS Resources**:
   - CPU utilization on EC2 instances
   - Connection count on RDS
   - HTTP 5XX errors on ALB

### Next Steps If ASR Not Met

- **Error rate > 5%**: Scale up EC2 instances or upgrade instance type
- **Latency > 5s**: Optimize Django views, add caching, scale database
- **Throughput low**: Check ALB connection limits, consider NLB

## 📁 File Structure

```
Arquisoft/
├── jmeter/                          ← NEW DIRECTORY
│   ├── load-test-asr.jmx            (18 KB - Main test plan)
│   ├── README.md                    (13 KB - Full documentation)
│   ├── QUICKSTART.md                (6 KB - Quick reference)
│   ├── run-load-test.sh             (6 KB - Execution script)
│   └── [results/]                   (Generated during test execution)
│
├── terraform/
│   ├── deployment.tf                (AWS infrastructure)
│   ├── install_terraform.sh
│   └── README.md
│
├── finops_platform/
│   ├── settings.py                  (PostgreSQL config)
│   └── urls.py
│
├── reportes/
│   └── views.py                     (API endpoints)
│
├── autenticacion/
│   ├── views.py                     (Login endpoint)
│   └── utilities.py
│
├── .gitignore                       (Updated with jmeter/ patterns)
└── manage.py
```

## 🎯 Success Criteria

Test is **SUCCESSFUL** when:

✅ **Availability**: Error rate < 5% (= 95%+ success)
✅ **Latency**: Average response time 2,000-5,000 ms
✅ **Consistency**: 95th percentile latency < 7,000 ms
✅ **Stability**: No cascading failures or timeout spike at peak load
✅ **Throughput**: Maintains 100+ req/sec at full 12K user load

## 📞 Support & Troubleshooting

**Common Issues**:
1. "Connection refused" → Check ALB DNS and security groups
2. "401 Unauthorized" → Verify report_user credentials and JWT extraction
3. "502 Bad Gateway" → Check EC2 instance health and Django app status
4. "504 Gateway Timeout" → App too slow, scale or optimize

**Resources**:
- JMeter Documentation: https://jmeter.apache.org/usermanual/
- Arquisoft Terraform: `terraform/README.md`
- Django Settings: `finops_platform/settings.py`

---

## Completion Status

| Item | Status | Details |
|------|--------|---------|
| JMeter test plan | ✅ Complete | 12,000 users, 10-min ramp-up, JWT auth |
| Documentation | ✅ Complete | README.md (13KB), QUICKSTART.md (6KB) |
| Execution script | ✅ Complete | run-load-test.sh for CLI mode |
| Directory structure | ✅ Complete | `/jmeter/` created with all files |
| Integration ready | ✅ Complete | Ready to test AWS infrastructure |
| Git untracked | ✅ Complete | New `jmeter/` directory ready to commit |

**Date Completed**: April 5, 2026
**All systems ready for ASR load testing** 🚀
