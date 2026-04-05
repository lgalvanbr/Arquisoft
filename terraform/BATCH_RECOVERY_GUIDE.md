# Batch Recovery Script - Automated Gunicorn Fix

## Overview

The `batch-recovery.sh` script automatically recovers gunicorn on **all app instances simultaneously** without manual SSH intervention.

**What it does:**
1. Connects to each instance via SSH
2. Copies the recovery script
3. Executes the recovery (reinstalls gunicorn + restarts service)
4. Reports success/failure for each instance

**Time:** ~4 minutes per instance × 4 instances = **~16 minutes total**

---

## Prerequisites

1. **SSH Key File** - Must have permissions (e.g., `~/arquisoft-key.pem`)
2. **Instance Public IPs** - Get from terraform output
3. **SSH Access** - Security group must allow port 22
4. **Bash Shell** - macOS, Linux, or WSL on Windows

---

## Step 1: Get Instance Public IPs

```bash
cd terraform
terraform output app_instances_public_ips
```

**Expected output:**
```json
{
  "a" = "203.0.113.45"
  "b" = "203.0.113.46"
  "c" = "203.0.113.47"
  "d" = "203.0.113.48"
}
```

Extract the IPs: `203.0.113.45 203.0.113.46 203.0.113.47 203.0.113.48`

---

## Step 2: Run Batch Recovery

```bash
# From project root
chmod +x terraform/batch-recovery.sh

terraform/batch-recovery.sh ~/path/to/key.pem 203.0.113.45 203.0.113.46 203.0.113.47 203.0.113.48
```

Or with environment variables:

```bash
export KEY_FILE=~/arquisoft-key.pem
export IPS="203.0.113.45 203.0.113.46 203.0.113.47 203.0.113.48"

terraform/batch-recovery.sh $KEY_FILE $IPS
```

---

## Example Output

```
==========================================
Batch Gunicorn Recovery Script
==========================================

Configuration:
  Key file: /home/user/arquisoft-key.pem
  Recovery script: /home/user/Arquisoft/terraform/recovery-gunicorn.sh
  Number of instances: 4
  Instance IPs: 203.0.113.45 203.0.113.46 203.0.113.47 203.0.113.48

[1/4] Recovering instance: 203.0.113.45
  • Copying recovery script...
  • Executing recovery script...
    Starting Gunicorn Recovery Script
    [1/5] Verifying repository access...
    ✓ Repository found at /apps/Arquisoft
    ...
  ✓ Instance 203.0.113.45 recovered successfully

[2/4] Recovering instance: 203.0.113.46
  ...
  ✓ Instance 203.0.113.46 recovered successfully

[3/4] Recovering instance: 203.0.113.47
  ...
  ✓ Instance 203.0.113.47 recovered successfully

[4/4] Recovering instance: 203.0.113.48
  ...
  ✓ Instance 203.0.113.48 recovered successfully

==========================================
Recovery Summary
==========================================
Successful: 4
Failed: 0

✓ All instances recovered successfully!

Next steps:
  1. Wait 30-60 seconds for ALB health checks to update
  2. Check ALB target health:
     aws elbv2 describe-target-health --target-group-arn <ARN> --region us-east-1
  3. Verify application is responding:
     curl http://<ALB_DNS>/api/reportes/health
```

---

## Step 3: Verify Recovery

### Option A: Check ALB Health (Recommended)

```bash
# Get target group ARN from terraform
cd terraform
TG_ARN=$(terraform output target_group_arn | tr -d '"')

# Check target health
aws elbv2 describe-target-health --target-group-arn $TG_ARN --region us-east-1
```

**Expected output:**
```json
{
  "TargetHealthDescriptions": [
    {
      "Target": {
        "Id": "i-0123456789abcdef0",
        "Port": 8080
      },
      "TargetHealth": {
        "State": "healthy",
        "Reason": "N/A",
        "Description": "N/A"
      }
    },
    ...
  ]
}
```

**All targets should show `"State": "healthy"`**

### Option B: Test via ALB

```bash
# Get ALB DNS name
ALB_DNS=$(cd terraform && terraform output alb_dns_name | tr -d '"')

# Test health endpoint
curl -v http://$ALB_DNS/api/reportes/health
```

**Expected response:**
```
HTTP/1.1 200 OK
Content-Type: application/json
...
```

### Option C: Direct SSH Check

```bash
# SSH to one instance
ssh -i ~/arquisoft-key.pem ubuntu@203.0.113.45

# Check service status
sudo systemctl status gunicorn

# Should show: Active: active (running)
```

---

## Troubleshooting

### "Failed to copy script" Error

```
scp: command not found
```

**Solution:** Install openssh-client
```bash
# macOS
brew install openssh

# Ubuntu/Debian
sudo apt-get install openssh-client

# Windows (WSL)
sudo apt-get install openssh-client
```

### "Permission denied" Error

```
Permission denied (publickey).
```

**Solutions:**
1. Check key file permissions:
   ```bash
   chmod 400 ~/arquisoft-key.pem
   ```

2. Verify key file is correct:
   ```bash
   ssh -i ~/arquisoft-key.pem ubuntu@<IP> "echo OK"
   ```

3. Check security group allows SSH (port 22) from your IP

### Script Times Out

**Possible causes:**
- Network connectivity issues
- Security group blocking port 22
- Instance taking too long to start

**Solution:** Run recovery on single instance manually:
```bash
ssh -i ~/arquisoft-key.pem ubuntu@<IP>
bash /tmp/recovery-gunicorn.sh
```

### "Recovery failed" Message

**Check logs on the instance:**
```bash
ssh -i ~/arquisoft-key.pem ubuntu@<IP>
tail -100 /var/log/recovery-gunicorn.log
```

---

## What Happens Inside Each Instance

1. **Verify repository:** Check `/apps/Arquisoft` exists
2. **Pull latest:** `git fetch && git checkout requirements.txt`
3. **Upgrade pip:** `pip3 install --upgrade pip`
4. **Install dependencies:** `pip3 install -r requirements.txt`
5. **Restart service:** `systemctl restart gunicorn`
6. **Verify:** Check service is running

See `recovery-gunicorn.sh` for detailed steps.

---

## Timing Expectations

| Phase | Duration | Notes |
|-------|----------|-------|
| SSH connection | 10 sec | Per instance |
| Copy script | 5 sec | Small script (< 5KB) |
| Git fetch | 30 sec | Download changes |
| Pip install | 60-90 sec | Install packages |
| Service restart | 10 sec | Systemd restart |
| Verification | 10 sec | Health checks |
| **Per Instance** | **~150 sec** | ~2.5 minutes |
| **4 Instances** | **~600 sec** | ~10 minutes (sequential) |
| **ALB health update** | **60 sec** | 2 checks × 30s interval |
| **Total** | **~11 minutes** | Sequential execution |

---

## Parallel vs Sequential Execution

**Current script:** Sequential (one instance at a time)
- **Pro:** Easier to debug, clear output
- **Con:** Takes ~10 minutes for 4 instances

**For faster recovery (advanced):**
```bash
# Run in parallel (background processes)
for ip in 203.0.113.45 203.0.113.46 203.0.113.47 203.0.113.48; do
  (terraform/batch-recovery.sh ~/key.pem $ip) &
done
wait
```
This would reduce time to ~3 minutes, but harder to monitor.

---

## Rollback (If Something Goes Wrong)

The recovery script **only installs packages**, no destructive operations.

**To rollback:**
1. SSH to affected instances
2. Manually downgrade if needed (unlikely necessary)
3. Or terminate and redeploy (cleaner approach)

```bash
cd terraform
terraform destroy -auto-approve
terraform apply -auto-approve
```

New instances will automatically have gunicorn installed ✅

---

## Post-Recovery Checklist

- [ ] Batch recovery script executed without errors
- [ ] All 4 instances show successful recovery
- [ ] ALB target health shows "healthy" for all targets
- [ ] `curl http://<ALB_DNS>/api/reportes/health` returns 200 OK
- [ ] Application responds to requests through load balancer
- [ ] CloudWatch logs show gunicorn running without errors
- [ ] No "No module named gunicorn" errors in systemd logs

---

## Next Steps After Recovery

1. ✅ **Gunicorn running:** Now have functional app servers
2. 🟠 **IMMEDIATE:** Implement Phase 1 security fixes (see TECHNICAL_REVIEW.md)
   - Close database to public (0.0.0.0/0 → app servers only)
   - Implement Secrets Manager for credentials
   - Set DEBUG=False in production
3. 🟡 **MEDIUM:** Phase 2 operational improvements
4. 🟢 **BEFORE PROD:** Phase 3 capacity scaling for 12K users

See `TECHNICAL_REVIEW.md` Section 11 for complete roadmap.

---

## Support

**All recovery outputs saved to:** `/var/log/recovery-gunicorn.log` on each instance

**To view recovery logs:**
```bash
ssh -i ~/key.pem ubuntu@<IP>
cat /var/log/recovery-gunicorn.log
```

---

**Status:** Script ready to execute  
**Files:** `batch-recovery.sh`, `recovery-gunicorn.sh`  
**Estimated Recovery Time:** 10-12 minutes total  
**Success Rate:** High (only installs packages, no complex operations)
