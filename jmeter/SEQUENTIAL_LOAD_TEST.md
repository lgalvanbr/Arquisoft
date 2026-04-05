# JMeter Sequential Load Test - Configuration Updated

## Change Summary

The JMeter test plan has been updated to run **sequentially** instead of simultaneously.

### What Changed

| Property | Before | After | Impact |
|----------|--------|-------|--------|
| **serialize_threadgroups** | `false` (parallel) | `true` (sequential) | ThreadGroups now run one after another |
| **Phase 1 ramp-up** | 600s | 0s | 5K users load instantly |
| **Test Name** | "Base 5K + Incremental 7K" | "Sequential: 5K then 7K" | Clarity on execution order |

---

## Execution Timeline

### Phase 1: Base Load (5,000 instant users)
```
Time: 0:00 - 10:00 (600 seconds)
Users: 5,000 instantaneously (ramp_time: 0s)
Duration: 600 seconds
Endpoints: GET /api/reportes/proyecto, GET /api/reportes/consumo
```

### Phase 2: Incremental Load (7,000 ramped users)
```
Time: 10:00 - 20:00 (600 seconds) 
Users: 7,000 gradually added (ramp_time: 600s = ~11.67 users/sec)
Duration: 600 seconds
Endpoints: GET /api/reportes/proyecto, GET /api/reportes/consumo
```

### Total Test Duration
```
Phase 1: 600s
Phase 2: 600s
Total: 1,200 seconds = 20 minutes
```

---

## Load Profile Visualization

```
Users
  |
12K |                                     ┌─────────────
    |                                    ╱
 7K |                    ┌──────────────╱
    |                   ╱
 5K |    ╱──────────────
    |   ╱
  0 |__╱________________╱________________
    0:00        5:00       10:00       15:00       20:00
    Phase 1    Phase 2
    (Constant)  (Ramp-up)
```

---

## How to Run

### Option 1: GUI (JMeter with GUI)
```bash
jmeter -t jmeter/load-test-asr.jmx
```

### Option 2: Headless (Recommended)
```bash
jmeter -n -t jmeter/load-test-asr.jmx \
        -l results/load-test-results.jtl \
        -j results/load-test.log
```

### Option 3: Run Script
```bash
bash jmeter/run-load-test.sh
```

---

## Expected Behavior

### Phase 1 (0:00 - 10:00)
- 5,000 users appear instantly
- High initial spike in traffic
- Server handles sudden load
- Observe latency, error rate, CPU usage spike

### Phase 2 (10:00 - 20:00)
- Additional 7,000 users gradually added
- Total reaches 12,000 by end of ramp-up (at 20:00)
- Monitor how system handles incremental load
- Observe if performance degrades with higher user count

---

## ASR Validation Metrics

During execution, monitor:

| Metric | Phase 1 | Phase 2 | Requirement |
|--------|---------|---------|-------------|
| **Concurrent Users** | 5,000 | 5K → 12K (ramp) | ≤ 12,000 ✓ |
| **Response Time (p50)** | 2-5s | 2-5s | < 5s |
| **Response Time (p95)** | 5-7s | 5-7s | < 7s |
| **Error Rate** | < 5% | < 5% | < 5% |
| **Availability** | > 95% | > 95% | ≥ 95% |

---

## Key Differences from Parallel Execution

### Previous (Parallel)
- Both ThreadGroups start at same time
- 12,000 users appear instantly
- Cannot isolate Phase 1 performance
- Harder to analyze bottlenecks
- Combined load harder to diagnose

### New (Sequential)
- Phase 1: Measure 5K user baseline performance
- Phase 2: See degradation with additional 7K users
- Clear separation for analysis
- Easier to identify bottlenecks
- Better for understanding infrastructure limits

---

## Results Analysis

### Expected Results File
```
results/load-test-results.jtl  (CSV with all samples)
results/load-test.log          (JMeter execution log)
```

### Key Metrics to Review
1. **Summary Report:** Avg response time, error rate, throughput
2. **Response Time Graph:** Latency trends over time
3. **Aggregate Report:** Min/Max/Avg per endpoint

---

## Troubleshooting

### If Phase 2 doesn't start after Phase 1
- Verify `serialize_threadgroups` is `true` in test plan
- Check JMeter logs for errors
- Ensure sufficient system resources

### If all users start at once despite configuration
- Reload test plan in JMeter GUI
- Clear JMeter cache
- Re-run test

### To Stop Test Early
- Press Ctrl+C in terminal
- Or click Stop button in JMeter GUI
- Data up to that point will be saved

---

## Files Modified

```
jmeter/load-test-asr.jmx
- Line 4: Changed testname to "Sequential: 5K then 7K"
- Line 10: Changed serialize_threadgroups false → true
- Line 13: Changed ramp_time 600 → 0 (Phase 1)
- Line 13: Changed testname to "Phase 1: Base Load..."
- Line 85: Changed testname to "Phase 2: Incremental Load..."
```

---

## Validation Checklist

After running the test:

- [ ] Test ran for ~20 minutes total
- [ ] Phase 1 (first 10 min) shows stable 5K users
- [ ] Phase 2 (next 10 min) shows users ramping from 5K to 12K
- [ ] Summary Report shows aggregated stats
- [ ] Response Time Graph shows time progression
- [ ] Error rate is tracked properly
- [ ] No "Both ThreadGroups running" message in logs

---

**Test Plan Updated:** 2026-04-05  
**Configuration:** Sequential (serialize_threadgroups: true)  
**Total Duration:** 20 minutes  
**Peak Load:** 12,000 concurrent users
