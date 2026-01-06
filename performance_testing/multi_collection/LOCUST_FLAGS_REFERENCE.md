# Locust Flags & Parameters Reference for Hybrid Locustfile

## Basic Command Structure

```bash
locust -f locustfile_hybrid_09.py [FLAGS]
```

---

## Common Flags Used in This Project

### Required Flags

| Flag | Description | Example | Notes |
|------|-------------|---------|-------|
| `-f, --locustfile` | Specify the locustfile to run | `-f locustfile_hybrid_09.py` | Required (or use positional arg) |

### Load Configuration Flags

| Flag | Description | Example | Notes |
|------|-------------|---------|-------|
| `--users` | Number of concurrent users | `--users 100` | Total concurrent users |
| `--spawn-rate` | Users spawned per second | `--spawn-rate 5` | Ramp-up rate |
| `--run-time` | Test duration | `--run-time 5m` | Format: `30s`, `5m`, `1h` |

### Output Flags

| Flag | Description | Example | Notes |
|------|-------------|---------|-------|
| `--headless` | Run without web UI | `--headless` | Required for automated runs |
| `--html` | Generate HTML report | `--html report.html` | Output file path |
| `--csv` | Generate CSV reports | `--csv results/prefix` | Creates multiple CSV files |
| `--csv-full-history` | Include all stats in CSV | `--csv-full-history` | More detailed CSV |

### Host Configuration

| Flag | Description | Example | Notes |
|------|-------------|---------|-------|
| `-H, --host` | Target host URL | `-H http://localhost:8080` | Overrides `host` in locustfile |
| `--web-host` | Web UI host | `--web-host 0.0.0.0` | Default: `*` (all interfaces) |
| `--web-port` | Web UI port | `--web-port 8089` | Default: `8089` |

### Advanced Flags

| Flag | Description | Example | Notes |
|------|-------------|---------|-------|
| `--loglevel` | Logging level | `--loglevel INFO` | Options: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `--logfile` | Log file path | `--logfile locust.log` | Write logs to file |
| `--expect-workers` | Expected worker count | `--expect-workers 2` | For distributed mode |
| `--master` | Run as master | `--master` | For distributed testing |
| `--worker` | Run as worker | `--worker` | For distributed testing |
| `--master-host` | Master host | `--master-host 192.168.1.100` | For distributed mode |
| `--master-port` | Master port | `--master-port 5557` | Default: `5557` |
| `--stop-timeout` | Stop timeout (seconds) | `--stop-timeout 30` | Wait time before force stop |

---

## Example Commands from This Project

### Basic Headless Run
```bash
locust -f locustfile_hybrid_09.py --users 100 --spawn-rate 5 --run-time 5m --headless
```

### With HTML Report
```bash
locust -f locustfile_hybrid_09.py --users 100 --spawn-rate 5 --run-time 5m --headless \
    --html hybrid_09_report.html
```

### With HTML and CSV Reports (as used in scripts)
```bash
locust -f locustfile_hybrid_09.py --users 200 --spawn-rate 33 --run-time 30m --headless \
    --html reports_RF3_U200_L200/hybrid_09_report.html \
    --csv reports_RF3_U200_L200/hybrid_09
```

### Quick Test (Low Load)
```bash
locust -f locustfile_hybrid_09.py --users 10 --spawn-rate 2 --run-time 30s --headless
```

### With Custom Host
```bash
locust -f locustfile_hybrid_09.py --users 100 --spawn-rate 5 --run-time 5m --headless \
    -H http://your-weaviate-server:8080
```

### With Logging
```bash
locust -f locustfile_hybrid_09.py --users 100 --spawn-rate 5 --run-time 5m --headless \
    --loglevel DEBUG --logfile locust.log
```

### Interactive Mode (with Web UI)
```bash
locust -f locustfile_hybrid_09.py --web-host 0.0.0.0 --web-port 8089
```
Then open browser to `http://localhost:8089`

---

## Environment Variables

The hybrid locustfile also respects these environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `FASTAPI_URL` | FastAPI endpoint URL | `FASTAPI_URL=http://localhost:8000` |
| `WEAVIATE_URL` | Weaviate URL (from config.py) | Set in `config.py` |

---

## Common Usage Patterns

### Pattern 1: Quick Verification
```bash
locust -f locustfile_hybrid_09.py --users 2 --spawn-rate 1 --run-time 20s --headless
```

### Pattern 2: Standard Test
```bash
locust -f locustfile_hybrid_09.py --users 100 --spawn-rate 5 --run-time 5m --headless \
    --html report.html --csv results
```

### Pattern 3: High Load Test
```bash
locust -f locustfile_hybrid_09.py --users 400 --spawn-rate 66 --run-time 30m --headless \
    --html high_load_report.html --csv high_load_results
```

### Pattern 4: Distributed Testing (Master)
```bash
locust -f locustfile_hybrid_09.py --master --users 1000 --spawn-rate 10 --run-time 10m --headless
```

### Pattern 5: Distributed Testing (Worker)
```bash
locust -f locustfile_hybrid_09.py --worker --master-host 192.168.1.100
```

---

## CSV Output Files Generated

When using `--csv prefix`, Locust generates:
- `prefix_stats.csv` - Request statistics
- `prefix_stats_history.csv` - Historical stats (if `--csv-full-history`)
- `prefix_failures.csv` - Failure details
- `prefix_exceptions.csv` - Exception details

---

## Notes

1. **Query File**: The locustfile expects `queries/queries_hybrid_09_200.json` to exist. If missing, generate it:
   ```bash
   python ../../utilities/generate_all_queries.py --type multi --search-types hybrid_09 --limits 200
   ```

2. **Host**: The host is set from `config.WEAVIATE_URL` in the locustfile. Override with `-H` flag if needed.

3. **Spawn Rate**: Calculated as `users / 6` in scripts for ~6 second ramp-up. Minimum recommended: 10.

4. **Run Time Format**: Supports `s` (seconds), `m` (minutes), `h` (hours). Examples: `30s`, `5m`, `1h`.

5. **Headless Mode**: Required for automated scripts. Omit for interactive web UI.

---

## Help Command

To see all available flags:
```bash
locust --help
```


