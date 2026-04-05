# JMeter ASR Load Test - Quick Start Guide

## Summary

The JMeter load test infrastructure is now complete. All files are ready for ASR validation of the Arquisoft FinOps platform deployed on AWS.

## Created Files

```
/jmeter/
├── load-test-asr.jmx              (JMeter test plan - Public endpoints)
├── README.md                        (Comprehensive documentation)
└── run-load-test.sh               (Execution script)
```

## Quick Start (2 Steps)

### Step 1: Get Your ALB DNS

After Terraform deployment:

```bash
cd terraform
terraform output alb_dns_name
# Output example: report-alb-1438726031.us-east-1.elb.amazonaws.com
```

### Step 2: Run the Load Test

**Option A (GUI - Recommended first run):**
```bash
jmeter -t jmeter/load-test-asr.jmx
# Replace YOUR_ALB_DNS_HERE in the GUI, then click Start
```

**Option B (CLI - Headless, generates HTML report):**
```bash
bash jmeter/run-load-test.sh ./results report-alb-1438726031.us-east-1.elb.amazonaws.com
# Results: ./results/results_html/index.html
```

## Test Configuration

| Setting | Value |
|---------|-------|
| **Concurrent Users** | 5,000 → 12,000 (ramp-up over 10 minutes) |
| **Test Duration** | 600 seconds (ends when all users are spawned) |
| **Endpoints** | `/api/reportes/proyecto` + `/api/reportes/consumo` (alternating) |
| **Authentication** | None (public endpoints) |
| **Request Timeout** | 30 seconds per request |

## ASR Success Criteria

Test **PASSES** if:
- ✅ Error rate < 5% (= 95% availability)
- ✅ Average latency: 2,000-5,000 ms
- ✅ 95th percentile latency < 7,000 ms
- ✅ No cascading failures (errors don't spike during ramp-up)

## Key Metrics to Watch

### During Test (JMeter GUI):

1. **Summary Report**: Real-time statistics as users are added
   - Watch "Samples" column: should reach ~1M+ samples
   - Watch "Average" column: should stay <5,000 ms
   - Watch "Error %" column: should stay <5%

2. **Response Time Graph**: Visual latency trend
   - Should be relatively flat during ramp-up
   - Spike indicates capacity limit approaching

3. **Aggregate Report** (Final Results):
   - p50 (Average): Target 2,000-5,000 ms
   - p95: Target <7,000 ms
   - Error %: Target <5%

### AWS Console (During Test):

Monitor these CloudWatch metrics:

```
EC2 Instances (report-app-lb-a, report-app-lb-b):
  • CPU Utilization: Should peak <80%
  • Network In: Should scale linearly with users

RDS (report-db):
  • CPU Utilization: Should stay <50%
  • Database Connections: Should not exceed connection limit

ALB (report-alb):
  • Target Health: All targets should remain "Healthy"
  • HTTP 5XX count: Should remain ~0
  • Latency: Compare with JMeter measurements
```

## API Endpoints

The test targets these **public endpoints** (no authentication):

- **GET /api/reportes/proyecto**
  - Returns project-level reporting data
  - No authentication required
  
- **GET /api/reportes/consumo**
  - Returns cloud consumption/usage data
  - No authentication required

## Troubleshooting

### Problem: "Connection refused" or "Unable to connect to ALB"

**Check:**
1. ALB DNS is correct (not `YOUR_ALB_DNS_HERE`)
2. Terraform deployment succeeded: `terraform output alb_dns_name`
3. Security group allows port 80 from your machine

### Problem: "HTTP 502 Bad Gateway" or "HTTP 503 Service Unavailable"

**Check:**
1. Target health in ALB: AWS Console → Load Balancers → Targets
2. Django app is running: SSH to instance → `sudo systemctl status django-app`
3. App logs for errors: `sudo tail -f /var/log/django-app.log`

### Problem: Test completes but latency is >10 seconds

**System is reaching capacity:**
1. Reduce concurrent users in load profile
2. Scale infrastructure (add EC2 instances or upgrade instance type)
3. Optimize Django views (add caching, database indexing)

## Performance Tuning (If ASR Not Met)

### If Error Rate > 5%:

```bash
# Add more EC2 instances to Target Group
cd terraform
# Edit deployment.tf: increase number of instances
terraform apply
```

### If Latency > 5 Seconds:

```bash
# Option 1: Scale instance type (t2.micro → t3.medium)
# Option 2: Add Django caching
# Option 3: Optimize database queries
# Option 4: Add read replicas to RDS
```

### If Throughput Too Low:

```bash
# Increase ALB connection limits
# Enable HTTP/2 (already configured)
# Consider NLB instead of ALB for extreme throughput
```

---

**Ready to test!** 🚀

Next: Run Step 2 above to start the load test.
