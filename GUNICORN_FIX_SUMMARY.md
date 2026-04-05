# GUNICORN FIX - Quick Reference Card

## Problem Summary

```
ERROR: /usr/bin/python3: No module named gunicorn
```

**Why it happened:**
- `gunicorn` was NOT in `requirements.txt`
- `user_data` script ran: `pip3 install -r requirements.txt`
- Gunicorn never got installed
- Systemd tried to start gunicorn → FAILED

**Timeline:**
1. EC2 instance boots → runs `user_data` script
2. Script installs Django, psycopg2, DRF, etc. (7 packages)
3. Script does NOT install gunicorn (not in requirements)
4. Script starts gunicorn service → ❌ FAILS with "No module named gunicorn"
5. Service enters failed state → Never recovers

---

## Solution Applied ✅

### Changes Made:

| File | Change | Impact |
|------|--------|--------|
| `requirements.txt` | Added `gunicorn==21.2.0` | New instances will auto-install gunicorn |
| `requirements.txt` | Added `gevent==23.9.1` | Optional: for async workers later |
| `requirements.txt` | Added `whitenoise==6.6.0` | Optional: static files serving |
| `terraform/recovery-gunicorn.sh` | New script | Recover existing instances |
| `terraform/GUNICORN_RECOVERY.md` | Recovery guide | Step-by-step instructions |
| `terraform/TECHNICAL_REVIEW.md` | AWS architecture review | Comprehensive analysis + 4-phase roadmap |

### For Existing Instances (In Production Now):

**Quick Fix (Choose ONE):**

**Option 1: SSH + Manual Commands** (Fastest)
```bash
# SSH to each app instance
ssh -i key.pem ubuntu@<IP>

# Pull latest requirements
sudo git -C /apps/Arquisoft fetch origin main
sudo git -C /apps/Arquisoft checkout origin/main -- requirements.txt

# Reinstall with gunicorn
sudo pip3 install -r /apps/Arquisoft/requirements.txt --break-system-packages

# Restart
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
```

**Option 2: Automated Script**
```bash
# Copy to instance
scp -i key.pem recovery-gunicorn.sh ubuntu@<IP>:/tmp/

# Execute
ssh -i key.pem ubuntu@<IP> "sudo bash /tmp/recovery-gunicorn.sh"
```

**Estimated Time:** ~4 minutes per instance × 4 instances = **16 minutes total**

---

## Verification Checklist

- [ ] SSH to instance works
- [ ] `/apps/Arquisoft/requirements.txt` contains `gunicorn==21.2.0`
- [ ] `python3 -c "import gunicorn"` returns no error
- [ ] `sudo systemctl status gunicorn` shows `active (running)`
- [ ] `sudo journalctl -u gunicorn -n 20` shows "Listening at: http://0.0.0.0:8080"
- [ ] AWS ALB target shows `Healthy`
- [ ] `curl http://<ALB_DNS>/api/reportes/health` returns 200 OK

---

## Future Prevention

**For new deployments:**
- ✅ `requirements.txt` now includes gunicorn
- ✅ `deployment.tf` will auto-install from requirements
- ✅ New instances won't have this problem

**Recommendation:**
Add validation to `user_data` script:
```bash
# After pip install, verify critical packages
if ! python3 -c "import gunicorn django" 2>/dev/null; then
    echo "FATAL: Missing critical dependencies" >&2
    exit 1
fi
```

---

## Root Cause Analysis

| Layer | Issue | Fix |
|-------|-------|-----|
| **Development** | `gunicorn` not in requirements.txt | ✅ FIXED |
| **Deployment** | No validation after `pip install` | ⏳ TODO: Add checks |
| **Monitoring** | No early warning of service failures | ⏳ TODO: CloudWatch alarms |
| **Documentation** | No checklist for troubleshooting | ✅ Added GUNICORN_RECOVERY.md |

---

## Related Findings (From Technical Review)

⚠️ **Other Critical Issues** (see `TECHNICAL_REVIEW.md`):
1. Database security group open to 0.0.0.0/0 (CRITICAL)
2. Hardcoded credentials in settings.py (CRITICAL)
3. DEBUG=True in production (CRITICAL)
4. SSH open to 0.0.0.0/0 (HIGH)
5. Capacity gap: 4K users vs 12K ASR target (HIGH)

📌 **Recommend:** Run Phase 1 security fixes BEFORE load testing

---

## Files Generated

```
terraform/
├── recovery-gunicorn.sh              ← Automated recovery script
├── GUNICORN_RECOVERY.md              ← Detailed recovery guide
├── TECHNICAL_REVIEW.md               ← Full AWS architecture review (6000+ words)
└── deployment.tf                     ← Original (unchanged, still valid)

requirements.txt                       ← MODIFIED: Added gunicorn + deps
```

## Commands Cheat Sheet

```bash
# Check if gunicorn installed
python3 -c "import gunicorn; print(gunicorn.__version__)"

# Check service status
sudo systemctl status gunicorn

# View service logs (last 50 lines)
sudo journalctl -u gunicorn -n 50 --no-pager

# View real-time logs
sudo journalctl -u gunicorn -f

# Restart service
sudo systemctl restart gunicorn

# Test health endpoint
curl http://localhost:8080/api/reportes/health
curl http://<ALB_DNS>/api/reportes/health

# Check port listening
sudo ss -tlnp | grep 8080
```

---

## Next Steps

1. ✅ **Immediate (15 min):** Run recovery on existing instances
2. 🟠 **SHORT TERM (1 hour):** Run Phase 1 security fixes (CRITICAL)
3. 🟡 **MEDIUM TERM (2-3 hours):** Phase 2 operational improvements
4. 🟢 **BEFORE PRODUCTION (5+ hours):** Phase 3 capacity scaling

See `TECHNICAL_REVIEW.md` Section 11 for detailed roadmap.

---

**Status:** Problem identified, fixed, and documented ✅  
**Commit:** `908cf83` - "fix: Add gunicorn and dependencies to requirements.txt"  
**Recovery Time:** ~20 minutes for all 4 instances  
**Deployment Status:** Ready for recovery, then Phase 1 security fixes
