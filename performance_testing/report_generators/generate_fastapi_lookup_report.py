"""
Generate combined performance test report for FastAPI lookup tests.
Aggregates results from Sync Lookup and Async Lookup tests across different user counts.
"""


import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import os
import csv
import json
from collections import defaultdict
from datetime import datetime


def parse_stats_csv(filepath):
    """Parse Locust stats CSV file"""
    stats = []
    try:
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                stats.append(row)
        return stats
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None


def extract_key_metrics(stats):
    """Extract key metrics from stats"""
    if not stats:
        return None
    
    # Get aggregated row (last row or row with "Aggregated" name)
    aggregated = None
    for row in stats:
        if row.get('Name') == 'Aggregated' or row.get('Type') == 'Aggregated':
            aggregated = row
            break
    
    if not aggregated:
        # If no aggregated row, use the main task row
        aggregated = stats[0] if stats else None
    
    if not aggregated:
        return None
    
    try:
        return {
            'total_requests': int(aggregated.get('Request Count', 0)),
            'failures': int(aggregated.get('Failure Count', 0)),
            'avg_response': float(aggregated.get('Average Response Time', 0)),
            'min_response': float(aggregated.get('Min Response Time', 0)),
            'max_response': float(aggregated.get('Max Response Time', 0)),
            'median_response': float(aggregated.get('Median Response Time', 0)),
            'p95_response': float(aggregated.get('95%', 0)),
            'p99_response': float(aggregated.get('99%', 0)),
            'rps': float(aggregated.get('Requests/s', 0)),
            'failure_rate': (int(aggregated.get('Failure Count', 0)) / max(int(aggregated.get('Request Count', 1)), 1)) * 100
        }
    except Exception as e:
        print(f"Error extracting metrics: {e}")
        return None


def scan_fastapi_lookup_reports():
    """Scan all lookup_* folders and gather data"""
    results = defaultdict(lambda: defaultdict(dict))
    
    # Get RF, Limit, and User Counts from environment variables (set by run script)
    rf_value = os.environ.get('PT_RF_VALUE', 'current')
    limit = os.environ.get('PT_LIMIT', '200')
    user_counts_str = os.environ.get('PT_USER_COUNTS', '')
    
    # Parse user counts from environment variable (space-separated string)
    if user_counts_str:
        user_counts = [uc.strip() for uc in user_counts_str.split() if uc.strip()]
    else:
        # Fallback: try to detect from folders if not provided
        import glob
        base_dir = '../reports/multi_collection'
        # Try new simplified pattern first: lookup_RF{rf}_U{users}_L{limit}
        pattern_new = os.path.join(base_dir, f"lookup_RF{rf_value}_U*_L{limit}")
        # Fallback to old pattern: fastapi_lookup_RF{rf}_Users{users}_Limit{limit}
        pattern_old = os.path.join(base_dir, f"fastapi_lookup_RF{rf_value}_Users*_Limit{limit}")
        folders = glob.glob(pattern_new) + glob.glob(pattern_old)
        user_counts = []
        for folder in folders:
            folder_name = os.path.basename(folder)
            try:
                # Try new pattern: lookup_RF{rf}_U{users}_L{limit}
                if folder_name.startswith('lookup_RF'):
                    parts = folder_name.split('_')
                    for i, part in enumerate(parts):
                        if part.startswith('U') and len(part) > 1:
                            user_count = part[1:]  # Remove 'U' prefix
                            if user_count.isdigit() and user_count not in user_counts:
                                user_counts.append(user_count)
                            break
                # Try old pattern: fastapi_lookup_RF{rf}_Users{users}_Limit{limit}
                else:
                    parts = folder_name.split('_')
                    for i, part in enumerate(parts):
                        if part == 'Users' and i + 1 < len(parts):
                            user_count = parts[i + 1]
                            if user_count not in user_counts:
                                user_counts.append(user_count)
                            break
            except Exception:
                continue
    
    if not user_counts:
        print(f"⚠️  No user counts found (checked PT_USER_COUNTS env var and folder scan)")
        return results
    
    print(f"📂 Processing user counts: {', '.join(sorted(user_counts, key=lambda x: int(x)))}")
    
    # FastAPI lookup reports folders
    base_dir = '../reports/multi_collection'
    
    # Search types for FastAPI lookup (BM25 and Hybrid)
    search_types = ['graphql_lookup_sync_bm25', 'graphql_lookup_async_bm25', 'graphql_lookup_sync', 'graphql_lookup_async']
    
    for user_count in sorted(user_counts, key=lambda x: int(x)):
        # Try new simplified pattern first: lookup_RF{rf}_U{users}_L{limit}
        folder_new = os.path.join(base_dir, f"lookup_RF{rf_value}_U{user_count}_L{limit}")
        # Fallback to old pattern: fastapi_lookup_RF{rf}_Users{users}_Limit{limit}
        folder_old = os.path.join(base_dir, f"fastapi_lookup_RF{rf_value}_Users{user_count}_Limit{limit}")
        folder = folder_new if os.path.exists(folder_new) else folder_old
        
        if not os.path.exists(folder):
            print(f"⚠️  Folder not found: {folder}")
            continue
        
        for search_type in search_types:
            stats_file = os.path.join(folder, f"{search_type}_stats.csv")
            
            if os.path.exists(stats_file):
                stats = parse_stats_csv(stats_file)
                metrics = extract_key_metrics(stats)
                
                # Only add if metrics exist and are non-zero
                if metrics and metrics.get('total_requests', 0) > 0:
                    results[user_count][search_type] = metrics
                    print(f"✓ Loaded: {folder}/{search_type}_stats.csv")
                elif metrics:
                    # File exists but has zero values, skip silently
                    pass
                else:
                    print(f"⚠️  Could not extract metrics from: {stats_file}")
            else:
                print(f"⚠️  File not found: {stats_file}")
    
    return results


def generate_html_report(results, rf_value, limit):
    """Generate comprehensive HTML report for FastAPI lookup tests"""
    
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>FastAPI Lookup Performance Test - Combined Report</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }
        h1 {
            margin: 0;
            font-size: 32px;
        }
        .subtitle {
            margin-top: 10px;
            opacity: 0.9;
        }
        .section {
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h2 {
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #667eea;
            color: white;
            font-weight: bold;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .metric-good {
            color: #22c55e;
            font-weight: bold;
        }
        .metric-warning {
            color: #eab308;
            font-weight: bold;
        }
        .metric-bad {
            color: #ef4444;
            font-weight: bold;
        }
        .summary-box {
            display: inline-block;
            padding: 15px 25px;
            margin: 10px;
            border-radius: 8px;
            background: #f0f9ff;
            border-left: 4px solid #667eea;
        }
        .summary-box h3 {
            margin: 0 0 10px 0;
            color: #667eea;
        }
        .summary-box p {
            margin: 5px 0;
            font-size: 24px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>FastAPI Lookup Performance Test - Combined Report</h1>
        <div class="subtitle">
            Comprehensive analysis: BM25 vs Hybrid (Sync & Async Lookup) across different user counts<br>
            RF: """ + rf_value + """ | Limit: """ + limit + """ | Query Types: BM25 & Hybrid (alpha=0.9)<br>
            Generated: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """
        </div>
    </div>
"""
    
    # Summary section
    html += """
    <div class="section">
        <h2>📊 Test Configuration</h2>
        <div>
            <div class="summary-box">
                <h3>User Counts Tested</h3>
                <p>""" + ", ".join(sorted(results.keys(), key=lambda x: int(x))) + """</p>
            </div>
            <div class="summary-box">
                <h3>Endpoints</h3>
                <p>/graphql/lookup<br>/graphql/async/lookup</p>
            </div>
            <div class="summary-box">
                <h3>Query Types</h3>
                <p>BM25 (keyword-only)<br>Hybrid (alpha=0.9)</p>
            </div>
            <div class="summary-box">
                <h3>Test Parameters</h3>
                <p>RF: """ + rf_value + """, Limit: """ + limit + """</p>
            </div>
            <div class="summary-box">
                <h3>Architecture</h3>
                <p>Sync: Single GraphQL query<br>Async: Parallel collection queries</p>
            </div>
        </div>
    </div>
"""
    
    # Table 1: Average Response Time Comparison - BM25
    html += """
    <div class="section">
        <h2>⏱️ Average Response Time Comparison - BM25 (ms)</h2>
        <table>
            <tr>
                <th>User Count</th>
                <th>Sync Lookup</th>
                <th>Async Lookup</th>
                <th>Difference</th>
            </tr>
"""
    
    for user_count in sorted(results.keys(), key=lambda x: int(x)):
        sync_metrics = results[user_count].get('graphql_lookup_sync_bm25', {})
        async_metrics = results[user_count].get('graphql_lookup_async_bm25', {})
        
        sync_avg = sync_metrics.get('avg_response', 0)
        async_avg = async_metrics.get('avg_response', 0)
        
        html += f"            <tr><td><b>{user_count} users</b></td>"
        
        if sync_avg == 0:
            html += "<td>-</td>"
        elif sync_avg < 500:
            html += f'<td class="metric-good">{sync_avg:.1f}</td>'
        elif sync_avg < 1000:
            html += f'<td class="metric-warning">{sync_avg:.1f}</td>'
        else:
            html += f'<td class="metric-bad">{sync_avg:.1f}</td>'
        
        if async_avg == 0:
            html += "<td>-</td>"
        elif async_avg < 500:
            html += f'<td class="metric-good">{async_avg:.1f}</td>'
        elif async_avg < 1000:
            html += f'<td class="metric-warning">{async_avg:.1f}</td>'
        else:
            html += f'<td class="metric-bad">{async_avg:.1f}</td>'
        
        # Calculate difference
        if sync_avg > 0 and async_avg > 0:
            diff = async_avg - sync_avg
            diff_pct = (diff / sync_avg) * 100
            if abs(diff_pct) < 5:
                html += f'<td class="metric-good">{diff:+.1f} ms ({diff_pct:+.1f}%)</td>'
            elif abs(diff_pct) < 15:
                html += f'<td class="metric-warning">{diff:+.1f} ms ({diff_pct:+.1f}%)</td>'
            else:
                html += f'<td class="metric-bad">{diff:+.1f} ms ({diff_pct:+.1f}%)</td>'
        else:
            html += "<td>-</td>"
        
        html += "</tr>\n"
    
    html += "        </table>\n    </div>\n"
    
    # Table 1b: Average Response Time Comparison - Hybrid
    html += """
    <div class="section">
        <h2>⏱️ Average Response Time Comparison - Hybrid (ms)</h2>
        <table>
            <tr>
                <th>User Count</th>
                <th>Sync Lookup</th>
                <th>Async Lookup</th>
                <th>Difference</th>
            </tr>
"""
    
    for user_count in sorted(results.keys(), key=lambda x: int(x)):
        sync_metrics = results[user_count].get('graphql_lookup_sync', {})
        async_metrics = results[user_count].get('graphql_lookup_async', {})
        
        sync_avg = sync_metrics.get('avg_response', 0)
        async_avg = async_metrics.get('avg_response', 0)
        
        html += f"            <tr><td><b>{user_count} users</b></td>"
        
        if sync_avg == 0:
            html += "<td>-</td>"
        elif sync_avg < 500:
            html += f'<td class="metric-good">{sync_avg:.1f}</td>'
        elif sync_avg < 1000:
            html += f'<td class="metric-warning">{sync_avg:.1f}</td>'
        else:
            html += f'<td class="metric-bad">{sync_avg:.1f}</td>'
        
        if async_avg == 0:
            html += "<td>-</td>"
        elif async_avg < 500:
            html += f'<td class="metric-good">{async_avg:.1f}</td>'
        elif async_avg < 1000:
            html += f'<td class="metric-warning">{async_avg:.1f}</td>'
        else:
            html += f'<td class="metric-bad">{async_avg:.1f}</td>'
        
        # Calculate difference
        if sync_avg > 0 and async_avg > 0:
            diff = async_avg - sync_avg
            diff_pct = (diff / sync_avg) * 100
            if abs(diff_pct) < 5:
                html += f'<td class="metric-good">{diff:+.1f} ms ({diff_pct:+.1f}%)</td>'
            elif abs(diff_pct) < 15:
                html += f'<td class="metric-warning">{diff:+.1f} ms ({diff_pct:+.1f}%)</td>'
            else:
                html += f'<td class="metric-bad">{diff:+.1f} ms ({diff_pct:+.1f}%)</td>'
        else:
            html += "<td>-</td>"
        
        html += "</tr>\n"
    
    html += "        </table>\n    </div>\n"
    
    # Table 2: 95th Percentile - BM25
    html += """
    <div class="section">
        <h2>📈 95th Percentile Response Time - BM25 (ms)</h2>
        <table>
            <tr>
                <th>User Count</th>
                <th>Sync Lookup</th>
                <th>Async Lookup</th>
            </tr>
"""
    
    for user_count in sorted(results.keys(), key=lambda x: int(x)):
        sync_metrics = results[user_count].get('graphql_lookup_sync_bm25', {})
        async_metrics = results[user_count].get('graphql_lookup_async_bm25', {})
        
        sync_p95 = sync_metrics.get('p95_response', 0)
        async_p95 = async_metrics.get('p95_response', 0)
        
        html += f"            <tr><td><b>{user_count} users</b></td>"
        
        if sync_p95 == 0:
            html += "<td>-</td>"
        elif sync_p95 < 1000:
            html += f'<td class="metric-good">{sync_p95:.1f}</td>'
        elif sync_p95 < 2000:
            html += f'<td class="metric-warning">{sync_p95:.1f}</td>'
        else:
            html += f'<td class="metric-bad">{sync_p95:.1f}</td>'
        
        if async_p95 == 0:
            html += "<td>-</td>"
        elif async_p95 < 1000:
            html += f'<td class="metric-good">{async_p95:.1f}</td>'
        elif async_p95 < 2000:
            html += f'<td class="metric-warning">{async_p95:.1f}</td>'
        else:
            html += f'<td class="metric-bad">{async_p95:.1f}</td>'
        
        html += "</tr>\n"
    
    html += "        </table>\n    </div>\n"
    
    # Table 2b: 95th Percentile - Hybrid
    html += """
    <div class="section">
        <h2>📈 95th Percentile Response Time - Hybrid (ms)</h2>
        <table>
            <tr>
                <th>User Count</th>
                <th>Sync Lookup</th>
                <th>Async Lookup</th>
            </tr>
"""
    
    for user_count in sorted(results.keys(), key=lambda x: int(x)):
        sync_metrics = results[user_count].get('graphql_lookup_sync', {})
        async_metrics = results[user_count].get('graphql_lookup_async', {})
        
        sync_p95 = sync_metrics.get('p95_response', 0)
        async_p95 = async_metrics.get('p95_response', 0)
        
        html += f"            <tr><td><b>{user_count} users</b></td>"
        
        if sync_p95 == 0:
            html += "<td>-</td>"
        elif sync_p95 < 1000:
            html += f'<td class="metric-good">{sync_p95:.1f}</td>'
        elif sync_p95 < 2000:
            html += f'<td class="metric-warning">{sync_p95:.1f}</td>'
        else:
            html += f'<td class="metric-bad">{sync_p95:.1f}</td>'
        
        if async_p95 == 0:
            html += "<td>-</td>"
        elif async_p95 < 1000:
            html += f'<td class="metric-good">{async_p95:.1f}</td>'
        elif async_p95 < 2000:
            html += f'<td class="metric-warning">{async_p95:.1f}</td>'
        else:
            html += f'<td class="metric-bad">{async_p95:.1f}</td>'
        
        html += "</tr>\n"
    
    html += "        </table>\n    </div>\n"
    
    # Table 3: Throughput - BM25
    html += """
    <div class="section">
        <h2>🔥 Throughput - BM25 (Requests/Second)</h2>
        <table>
            <tr>
                <th>User Count</th>
                <th>Sync Lookup</th>
                <th>Async Lookup</th>
            </tr>
"""
    
    for user_count in sorted(results.keys(), key=lambda x: int(x)):
        sync_metrics = results[user_count].get('graphql_lookup_sync_bm25', {})
        async_metrics = results[user_count].get('graphql_lookup_async_bm25', {})
        
        sync_rps = sync_metrics.get('rps', 0)
        async_rps = async_metrics.get('rps', 0)
        
        html += f"            <tr><td><b>{user_count} users</b></td>"
        
        if sync_rps == 0:
            html += "<td>-</td>"
        elif sync_rps > 30:
            html += f'<td class="metric-good">{sync_rps:.2f}</td>'
        elif sync_rps > 20:
            html += f'<td class="metric-warning">{sync_rps:.2f}</td>'
        else:
            html += f'<td class="metric-bad">{sync_rps:.2f}</td>'
        
        if async_rps == 0:
            html += "<td>-</td>"
        elif async_rps > 30:
            html += f'<td class="metric-good">{async_rps:.2f}</td>'
        elif async_rps > 20:
            html += f'<td class="metric-warning">{async_rps:.2f}</td>'
        else:
            html += f'<td class="metric-bad">{async_rps:.2f}</td>'
        
        html += "</tr>\n"
    
    html += "        </table>\n    </div>\n"
    
    # Table 3b: Throughput - Hybrid
    html += """
    <div class="section">
        <h2>🔥 Throughput - Hybrid (Requests/Second)</h2>
        <table>
            <tr>
                <th>User Count</th>
                <th>Sync Lookup</th>
                <th>Async Lookup</th>
            </tr>
"""
    
    for user_count in sorted(results.keys(), key=lambda x: int(x)):
        sync_metrics = results[user_count].get('graphql_lookup_sync', {})
        async_metrics = results[user_count].get('graphql_lookup_async', {})
        
        sync_rps = sync_metrics.get('rps', 0)
        async_rps = async_metrics.get('rps', 0)
        
        html += f"            <tr><td><b>{user_count} users</b></td>"
        
        if sync_rps == 0:
            html += "<td>-</td>"
        elif sync_rps > 30:
            html += f'<td class="metric-good">{sync_rps:.2f}</td>'
        elif sync_rps > 20:
            html += f'<td class="metric-warning">{sync_rps:.2f}</td>'
        else:
            html += f'<td class="metric-bad">{sync_rps:.2f}</td>'
        
        if async_rps == 0:
            html += "<td>-</td>"
        elif async_rps > 30:
            html += f'<td class="metric-good">{async_rps:.2f}</td>'
        elif async_rps > 20:
            html += f'<td class="metric-warning">{async_rps:.2f}</td>'
        else:
            html += f'<td class="metric-bad">{async_rps:.2f}</td>'
        
        html += "</tr>\n"
    
    html += "        </table>\n    </div>\n"
    
    # Detailed breakdown per user count
    for user_count in sorted(results.keys(), key=lambda x: int(x)):
        html += f"""
    <div class="section">
        <h2>📋 Detailed Metrics - {user_count} Users</h2>
        <table>
            <tr>
                <th>Endpoint</th>
                <th>Requests</th>
                <th>Failures</th>
                <th>Avg (ms)</th>
                <th>Median (ms)</th>
                <th>95% (ms)</th>
                <th>99% (ms)</th>
                <th>Min (ms)</th>
                <th>Max (ms)</th>
                <th>RPS</th>
                <th>Failure %</th>
            </tr>
"""
        
        for search_type, display_name in [
            ('graphql_lookup_sync_bm25', 'BM25 Sync Lookup (/graphql/lookup)'),
            ('graphql_lookup_async_bm25', 'BM25 Async Lookup (/graphql/async/lookup)'),
            ('graphql_lookup_sync', 'Hybrid Sync Lookup (/graphql/lookup)'),
            ('graphql_lookup_async', 'Hybrid Async Lookup (/graphql/async/lookup)')
        ]:
            metrics = results[user_count].get(search_type, {})
            
            if metrics:
                failure_class = 'metric-good' if metrics.get('failure_rate', 0) < 1 else ('metric-warning' if metrics.get('failure_rate', 0) < 5 else 'metric-bad')
                
                html += f"""
            <tr>
                <td><b>{display_name}</b></td>
                <td>{metrics.get('total_requests', 0):,}</td>
                <td>{metrics.get('failures', 0):,}</td>
                <td>{metrics.get('avg_response', 0):.1f}</td>
                <td>{metrics.get('median_response', 0):.1f}</td>
                <td>{metrics.get('p95_response', 0):.1f}</td>
                <td>{metrics.get('p99_response', 0):.1f}</td>
                <td>{metrics.get('min_response', 0):.1f}</td>
                <td>{metrics.get('max_response', 0):.1f}</td>
                <td>{metrics.get('rps', 0):.2f}</td>
                <td class="{failure_class}">{metrics.get('failure_rate', 0):.2f}%</td>
            </tr>
"""
            else:
                html += f"""
            <tr>
                <td><b>{display_name}</b></td>
                <td colspan="10" style="text-align: center; color: #999;">No data</td>
            </tr>
"""
        
        html += "        </table>\n    </div>\n"
    
    html += """
</body>
</html>
"""
    
    return html


def main():
    """Main function"""
    print("=" * 70)
    print("FASTAPI LOOKUP COMBINED PERFORMANCE REPORT GENERATOR")
    print("=" * 70)
    print("\nScanning FastAPI lookup reports folders...")
    print("-" * 70)
    
    # Scan all reports
    results = scan_fastapi_lookup_reports()
    
    if not results:
        print("\n❌ No data found!")
        print("   Make sure you have lookup_* folders with CSV files")
        print("   Expected pattern: lookup_RF{rf}_U{count}_L{limit}/")
        print("   (or old pattern: fastapi_lookup_RF{rf}_Users{count}_Limit{limit}/)")
        return 1
    
    print("\n" + "-" * 70)
    print(f"✅ Found data for {len(results)} user counts")
    print(f"   User counts: {', '.join(sorted(results.keys(), key=lambda x: int(x)))}")
    
    # Get RF and Limit from environment variables
    rf_value = os.environ.get('PT_RF_VALUE', 'current')
    limit = os.environ.get('PT_LIMIT', '200')
    
    # Generate HTML report
    print("\n📝 Generating combined FastAPI lookup HTML report...")
    html = generate_html_report(results, rf_value, limit)
    
    # Simplified naming: lookup_combined_RF{rf}_U{users}_L{limit}.html
    user_counts_sorted = sorted(results.keys(), key=lambda x: int(x))
    if len(user_counts_sorted) == 1:
        users_str = f"U{user_counts_sorted[0]}"
    else:
        # Multiple user counts: U100-200-300
        users_str = f"U{'-'.join(user_counts_sorted)}"
    
    output_file = f"../reports/multi_collection/lookup_combined_RF{rf_value}_{users_str}_L{limit}.html"
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"✅ Created: {output_file}")
    print(f"   Location: {os.path.abspath(output_file)}")
    print("\n" + "=" * 70)
    print("REPORT GENERATED!")
    print("=" * 70)
    print(f"\nOpen the report:")
    print(f"   {output_file}")
    print("\nOr in browser:")
    print(f"   open {output_file}")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

