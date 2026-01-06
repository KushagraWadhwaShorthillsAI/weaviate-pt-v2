"""
Generate combined performance test report from multiple test runs.
Aggregates results from different limits (10, 50, 100, 150, 200) and search types.
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


def scan_reports():
    """Scan all reports_* folders and gather data"""
    results = defaultdict(lambda: defaultdict(dict))
    
    # Single collection reports folders
    folders = ['../reports/single_collection/reports_10', '../reports/single_collection/reports_50', '../reports/single_collection/reports_100', '../reports/single_collection/reports_150', '../reports/single_collection/reports_200']
    
    # Search types (now includes vector)
    search_types = ['bm25', 'hybrid_01', 'hybrid_09', 'vector', 'mixed']
    
    for folder in folders:
        if not os.path.exists(folder):
            print(f"⚠️  Folder not found: {folder}")
            continue
        
        # Extract limit from folder name (reports_10 -> 10)
        folder_name = os.path.basename(folder)
        limit = folder_name.split('_')[-1]  # Get last part after underscore
        
        for search_type in search_types:
            stats_file = os.path.join(folder, f"{search_type}_stats.csv")
            
            if os.path.exists(stats_file):
                stats = parse_stats_csv(stats_file)
                metrics = extract_key_metrics(stats)
                
                if metrics:
                    results[limit][search_type] = metrics
                    print(f"✓ Loaded: {folder}/{search_type}_stats.csv")
                else:
                    print(f"⚠️  Could not extract metrics from: {stats_file}")
            else:
                print(f"⚠️  File not found: {stats_file}")
    
    return results


def generate_html_report(results):
    """Generate comprehensive HTML report"""
    
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Weaviate Performance Test - Combined Report</title>
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
        <h1>📈 Single Collection Performance Test - Combined Report</h1>
        <div class="subtitle">
            SongLyrics collection (1M objects) - All search types and limits<br>
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
                <h3>Result Limits Tested</h3>
                <p>""" + ", ".join(sorted(results.keys())) + """</p>
            </div>
            <div class="summary-box">
                <h3>Search Types</h3>
                <p>BM25, Hybrid 0.1, Hybrid 0.9, Vector, Mixed</p>
            </div>
            <div class="summary-box">
                <h3>Test Parameters</h3>
                <p>300 users, 5min, ramp-up 5/s</p>
            </div>
        </div>
    </div>
"""
    
    # Table 1: Response Time Comparison
    html += """
    <div class="section">
        <h2>⏱️ Average Response Time Comparison (ms)</h2>
        <table>
            <tr>
                <th>Result Limit</th>
                <th>BM25</th>
                <th>Hybrid α=0.1</th>
                <th>Hybrid α=0.9</th>
                <th>nearVector</th>
                <th>Mixed</th>
            </tr>
"""
    
    for limit in sorted(results.keys(), key=lambda x: int(x)):
        html += f"            <tr><td><b>Limit {limit}</b></td>"
        
        for search_type in ['bm25', 'hybrid_01', 'hybrid_09', 'vector', 'mixed']:
            metrics = results[limit].get(search_type, {})
            avg = metrics.get('avg_response', 0)
            
            if avg == 0:
                html += "<td>-</td>"
            elif avg < 500:
                html += f'<td class="metric-good">{avg:.1f}</td>'
            elif avg < 1000:
                html += f'<td class="metric-warning">{avg:.1f}</td>'
            else:
                html += f'<td class="metric-bad">{avg:.1f}</td>'
        
        html += "</tr>\n"
    
    html += "        </table>\n    </div>\n"
    
    # Table 2: 95th Percentile
    html += """
    <div class="section">
        <h2>📈 95th Percentile Response Time (ms)</h2>
        <table>
            <tr>
                <th>Result Limit</th>
                <th>BM25</th>
                <th>Hybrid α=0.1</th>
                <th>Hybrid α=0.9</th>
                <th>nearVector</th>
                <th>Mixed</th>
            </tr>
"""
    
    for limit in sorted(results.keys(), key=lambda x: int(x)):
        html += f"            <tr><td><b>Limit {limit}</b></td>"
        
        for search_type in ['bm25', 'hybrid_01', 'hybrid_09', 'vector', 'mixed']:
            metrics = results[limit].get(search_type, {})
            p95 = metrics.get('p95_response', 0)
            
            if p95 == 0:
                html += "<td>-</td>"
            elif p95 < 1000:
                html += f'<td class="metric-good">{p95:.1f}</td>'
            elif p95 < 2000:
                html += f'<td class="metric-warning">{p95:.1f}</td>'
            else:
                html += f'<td class="metric-bad">{p95:.1f}</td>'
        
        html += "</tr>\n"
    
    html += "        </table>\n    </div>\n"
    
    # Table 3: Throughput
    html += """
    <div class="section">
        <h2>🔥 Throughput (Requests/Second)</h2>
        <table>
            <tr>
                <th>Result Limit</th>
                <th>BM25</th>
                <th>Hybrid α=0.1</th>
                <th>Hybrid α=0.9</th>
                <th>nearVector</th>
                <th>Mixed</th>
            </tr>
"""
    
    for limit in sorted(results.keys(), key=lambda x: int(x)):
        html += f"            <tr><td><b>Limit {limit}</b></td>"
        
        for search_type in ['bm25', 'hybrid_01', 'hybrid_09', 'vector', 'mixed']:
            metrics = results[limit].get(search_type, {})
            rps = metrics.get('rps', 0)
            
            if rps == 0:
                html += "<td>-</td>"
            elif rps > 30:
                html += f'<td class="metric-good">{rps:.2f}</td>'
            elif rps > 20:
                html += f'<td class="metric-warning">{rps:.2f}</td>'
            else:
                html += f'<td class="metric-bad">{rps:.2f}</td>'
        
        html += "</tr>\n"
    
    html += "        </table>\n    </div>\n"
    
    # Detailed breakdown per limit
    for limit in sorted(results.keys(), key=lambda x: int(x)):
        html += f"""
    <div class="section">
        <h2>📋 Detailed Metrics - Limit {limit}</h2>
        <table>
            <tr>
                <th>Search Type</th>
                <th>Requests</th>
                <th>Failures</th>
                <th>Avg (ms)</th>
                <th>Median (ms)</th>
                <th>95% (ms)</th>
                <th>99% (ms)</th>
                <th>Min (ms)</th>
                <th>Max (ms)</th>
                <th>RPS</th>
            </tr>
"""
        
        for search_type, display_name in [
            ('bm25', 'BM25'),
            ('hybrid_01', 'Hybrid α=0.1'),
            ('hybrid_09', 'Hybrid α=0.9'),
            ('vector', 'nearVector'),
            ('mixed', 'Mixed')
        ]:
            metrics = results[limit].get(search_type, {})
            
            if metrics:
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
            </tr>
"""
            else:
                html += f"""
            <tr>
                <td><b>{display_name}</b></td>
                <td colspan="9" style="text-align: center; color: #999;">No data</td>
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
    print("COMBINED PERFORMANCE REPORT GENERATOR")
    print("=" * 70)
    print("\nScanning reports folders...")
    print("-" * 70)
    
    # Scan all reports
    results = scan_reports()
    
    if not results:
        print("\n❌ No data found!")
        print("   Make sure you have reports_* folders with CSV files")
        return 1
    
    print("\n" + "-" * 70)
    print(f"✅ Found data for {len(results)} limits")
    print(f"   Limits: {', '.join(sorted(results.keys(), key=lambda x: int(x)))}")
    
    # Generate HTML report
    print("\n📝 Generating combined HTML report...")
    html = generate_html_report(results)
    
    output_file = "../reports/single_collection/single_collection_report.html"
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"✅ Created: {output_file}")
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
