# GUNICORN MISSING MODULE - RECOVERY GUIDE

## Problem

```
Apr 05 22:25:57 ip-172-31-69-197 python3[3585]: /usr/bin/python3: No module named gunicorn
Apr 05 22:25:57 ip-172-31-69-197 systemd[1]: gunicorn.service: Failed with result 'exit-code'
```

**Root Cause:** `gunicorn` was not listed in `requirements.txt`, so the pip install failed silently during `user_data` script execution.

---

## Quick Fix (Immediate - 2 minutes)

### Option A: Manual SSH to Each Instance

1. **SSH to each application instance:**
   ```bash
   ssh -i your-key.pem ubuntu@<INSTANCE_PUBLIC_IP>
   ```

2. **Run the recovery script:**
   ```bash
   cd /apps/Arquisoft
   
   # Pull latest requirements.txt with gunicorn
   sudo git fetch origin main
   sudo git checkout origin/main -- requirements.txt
   
   # Reinstall all dependencies
   sudo pip3 install -r requirements.txt --break-system-packages
   
   # Restart gunicorn
   sudo systemctl restart gunicorn
   ```

3. **Verify it's working:**
   ```bash
   sudo journalctl -u gunicorn -f
   # Should show: Listening at: http://0.0.0.0:8080
   ```

### Option B: Automated Script (Recommended)

We've created a recovery script at `terraform/recovery-gunicorn.sh`:

```bash
# 1. Copy script to each instance
for ip in <APP_INSTANCE_IPS>; do
  scp -i your-key.pem recovery-gunicorn.sh ubuntu@$ip:/tmp/
done

# 2. Execute on each instance
for ip in <APP_INSTANCE_IPS>; do
  ssh -i your-key.pem ubuntu@$ip "bash /tmp/recovery-gunicorn.sh"
done
```

---

## Permanent Fix (Prevents Recurrence)

### Changes Made:

**File: `requirements.txt`**
```diff
  Django==4.2.0
  psycopg2-binary==2.9.6
  djangorestframework==3.14.0
  djangorestframework-simplejwt==5.2.2
  django-cors-headers==4.0.0
  python-decouple==3.8
  PyJWT==2.8.0
+ gunicorn==21.2.0
+ gevent==23.9.1
+ whitenoise==6.6.0
```

**Why these additions:**
- **gunicorn**: WSGI server (production application server)
- **gevent**: Async I/O library for better concurrency (optional, for gevent workers)
- **whitenoise**: Static file serving (recommended for production)

### New Deployments:

Since we've added gunicorn to `requirements.txt`, **new instances deployed with `terraform apply` will automatically install gunicorn** via the `user_data` script.

---

## Verification Steps

### 1. Check Gunicorn is Installed:
```bash
python3 -c "import gunicorn; print(f'Gunicorn {gunicorn.__version__}')"
```
**Expected output:** `Gunicorn 21.2.0` (or similar version)

### 2. Check Service Status:
```bash
sudo systemctl status gunicorn
```
**Expected output:**
```
● gunicorn.service - Gunicorn Arquisoft FinOps Application Server
   Loaded: loaded (/etc/systemd/system/gunicorn.service; enabled; vendor preset: enabled)
   Active: active (running) since Sun 2026-04-05 22:30:00 UTC; 5s ago
```

### 3. Check Logs:
```bash
sudo journalctl -u gunicorn -n 50 --no-pager
```
**Expected output:**
```
Apr 05 22:30:00 ip-172-31-69-197 python3[3585]: [2026-04-05 22:30:00 +0000] [3585] [INFO] Starting gunicorn 21.2.0
Apr 05 22:30:00 ip-172-31-69-197 python3[3585]: [2026-04-05 22:30:00 +0000] [3585] [INFO] Listening at: http://0.0.0.0:8080 (3585)
Apr 05 22:30:00 ip-172-31-69-197 python3[3585]: [2026-04-05 22:30:00 +0000] [3585] [INFO] Using worker: sync
Apr 05 22:30:00 ip-172-31-69-197 python3[3585]: [2026-04-05 22:30:00 +0000] [3589] [INFO] Booting worker with pid: 3589
Apr 05 22:30:00 ip-172-31-69-197 python3[3585]: [2026-04-05 22:30:00 +0000] [3590] [INFO] Booting worker with pid: 3590
Apr 05 22:30:00 ip-172-31-69-197 python3[3585]: [2026-04-05 22:30:00 +0000] [3591] [INFO] Booting worker with pid: 3591
Apr 05 22:30:00 ip-172-31-69-197 python3[3585]: [2026-04-05 22:30:00 +0000] [3592] [INFO] Booting worker with pid: 3592
```

### 4. Test Application:
```bash
# From ALB DNS name or app instance IP
curl -v http://<ALB_DNS>/api/reportes/health

# Expected response:
HTTP/1.1 200 OK
...
```

---

## Health Check in ALB

The ALB should now:
1. Health check path: `/api/reportes/health`
2. Expected status: `200 OK`
3. Check interval: 30 seconds
4. Healthy threshold: 2 checks

**Check ALB target health:**
```bash
# Via AWS CLI
aws elbv2 describe-target-health \
  --target-group-arn <TARGET_GROUP_ARN> \
  --region us-east-1
```

Expected output:
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
    }
  ]
}
```

---

## Troubleshooting

### Still Getting "No module named gunicorn"?

1. **Verify git pull worked:**
   ```bash
   cat /apps/Arquisoft/requirements.txt | grep gunicorn
   ```
   Should show: `gunicorn==21.2.0`

2. **Force reinstall pip packages:**
   ```bash
   sudo pip3 install --force-reinstall --no-cache-dir -r requirements.txt --break-system-packages
   ```

3. **Check systemd service definition:**
   ```bash
   cat /etc/systemd/system/gunicorn.service
   ```
   Should have: `ExecStart=/usr/bin/python3 -m gunicorn ...`

### Port 8080 Already in Use?

```bash
sudo lsof -i :8080
# Kill the process if needed
sudo kill -9 <PID>
# Restart gunicorn
sudo systemctl restart gunicorn
```

### Service Won't Start After Fix?

```bash
# Check for errors in dependencies
sudo python3 -c "import django; import gunicorn; print('OK')"

# Run gunicorn manually to see errors
sudo python3 -m gunicorn \
  --workers 4 \
  --bind 0.0.0.0:8080 \
  finops_platform.wsgi:application
```

---

## Timeline for Full Recovery

| Step | Duration | Notes |
|------|----------|-------|
| SSH to first instance | 1 min | Get public IP from terraform output |
| Run recovery script | 2 min | Installs 10 packages, restarts service |
| Verify status | 1 min | Check journalctl and systemctl |
| **Per instance** | **4 min** | **Repeat for 4 app instances = 16 min total** |
| ALB health checks update | 2 min | Waits for 2 healthy checks @ 30s interval |
| **Total Recovery Time** | **~20 minutes** | All instances + ALB validation |

---

## Prevention for Future Deployments

### 1. Code Change (✅ Already Done)
Added gunicorn to `requirements.txt`

### 2. Terraform Improvement
The `deployment.tf` already has:
```bash
sudo pip3 install -r requirements.txt --break-system-packages
```
This will now correctly install gunicorn for new instances.

### 3. Better Error Handling
Future improvement to `user_data` script:
```bash
# Verify critical packages are installed
if ! python3 -c "import gunicorn" 2>/dev/null; then
    echo "ERROR: Gunicorn failed to install!" | tee -a /var/log/user-data-error.log
    exit 1
fi
```

---

## Questions?

- **Requirements.txt change confirmed?** Yes, check GitHub at `main` branch
- **Need to redeploy from scratch?** No, quick recovery fixes existing instances
- **Future deployments affected?** No, they'll automatically get gunicorn
- **Health checks working?** Should be after recovery script runs

**Status:** All app instances should be **healthy** within 20-25 minutes.
