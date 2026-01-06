"""
Generate Performance Report for Parallel Collection Testing
Analyzes results from parallel execution tests where 9 collections are queried simultaneously.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import csv
import json
import glob
from datetime import datetime
from collections import defaultdict


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
        # If no aggregated row, use the first task row
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


def find_latest_results_folder():
    """Find the most recent results_* folder"""
    # Check in reports/parallel_testing directory
    reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports', 'parallel_testing')
    results_folders = glob.glob(os.path.join(reports_dir, 'results_*'))
    if not results_folders:
        # Fallback to current directory (for backward compatibility)
        results_folders = glob.glob('results_*')
    if not results_folders:
        return None
    # Sort by name (which includes timestamp)
    results_folders.sort(reverse=True)
    # Return just the folder name, not full path
    return os.path.basename(results_folders[0])


def scan_parallel_results(results_folder):
    """Scan parallel test results folder and gather data"""
    results = {}
    
    # Check if results_folder is a full path or just a name
    if os.path.isabs(results_folder) or os.path.exists(results_folder):
        folder_path = results_folder
    else:
        # Try in reports/parallel_testing first, then current directory
        reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports', 'parallel_testing')
        folder_path = os.path.join(reports_dir, results_folder)
        if not os.path.exists(folder_path):
            folder_path = results_folder  # Fallback to current directory
    
    if not os.path.exists(folder_path):
        print(f"\n❌ Folder not found: {results_folder}")
        print(f"   Tried: {folder_path}")
        return results
    
    print(f"\n📂 Scanning: {folder_path}/")
    print("=" * 70)
    
    # Map test names to search types
    test_mapping = {
        '1_Vector': 'vector',
        '2_BM25': 'bm25',
        '3_Hybrid_01': 'hybrid_01',
        '4_Hybrid_09': 'hybrid_09',
        '5_Mixed': 'mixed'
    }
    
    for test_prefix, search_type in test_mapping.items():
        # Find stats file (e.g., 1_Vector_limit200_stats.csv)
        pattern = os.path.join(folder_path, f"{test_prefix}_limit*_stats.csv")
        stats_files = glob.glob(pattern)
        
        if stats_files:
            stats_file = stats_files[0]  # Take first match
            stats = parse_stats_csv(stats_file)
            metrics = extract_key_metrics(stats)
            
            if metrics:
                results[search_type] = metrics
                print(f"✓ Loaded: {os.path.basename(stats_file)}")
            else:
                print(f"⚠️  Could not extract metrics from: {os.path.basename(stats_file)}")
        else:
            print(f"⚠️  No stats file found for: {test_prefix}")
    
    print("=" * 70)
    return results


def generate_html_report(results, results_folder):
    """Generate HTML report"""
    
    # Prepare data for charts
    search_types = ['bm25', 'hybrid_01', 'hybrid_09', 'vector', 'mixed']
    search_labels = {
        'bm25': 'BM25',
        'hybrid_01': 'Hybrid α=0.1',
        'hybrid_09': 'Hybrid α=0.9',
        'vector': 'Vector',
        'mixed': 'Mixed'
    }
    
    # Extract metrics for charts
    labels = [search_labels.get(st, st.upper()) for st in search_types if st in results]
    avg_times = [results[st]['avg_response'] for st in search_types if st in results]
    median_times = [results[st]['median_response'] for st in search_types if st in results]
    p95_times = [results[st]['p95_response'] for st in search_types if st in results]
    p99_times = [results[st]['p99_response'] for st in search_types if st in results]
    rps_values = [results[st]['rps'] for st in search_types if st in results]
    failure_rates = [results[st]['failure_rate'] for st in search_types if st in results]
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Parallel Collection Testing Report</title>
    <meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
        }}
        .info-box {{
            background: #e8f4f8;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .info-box strong {{
            color: #2980b9;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .metric-good {{
            color: #27ae60;
            font-weight: bold;
        }}
        .metric-warning {{
            color: #f39c12;
            font-weight: bold;
        }}
        .metric-bad {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .chart-container {{
            margin: 30px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 8px;
        }}
        canvas {{
            max-height: 400px;
        }}
        .summary-card {{
            display: inline-block;
            background: #fff;
            border: 2px solid #3498db;
            border-radius: 8px;
            padding: 20px;
            margin: 10px;
            min-width: 200px;
            text-align: center;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #2c3e50;
            font-size: 14px;
        }}
        .summary-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #3498db;
        }}
        .summary-card .unit {{
            font-size: 14px;
            color: #7f8c8d;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            color: #7f8c8d;
            font-size: 12px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Parallel Collection Testing Report</h1>
        
        <div class="info-box">
            <strong>Test Configuration:</strong> 9 collections queried in parallel (simultaneous HTTP requests)<br>
            <strong>Results Folder:</strong> {results_folder}<br>
            <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            <strong>Search Types Tested:</strong> {len(results)} types
        </div>

        <h2>📊 Performance Summary</h2>
        <div style="text-align: center;">
"""
    
    # Add summary cards
    if results:
        # Find best performer (lowest avg response time)
        best_st = min(results.keys(), key=lambda x: results[x]['avg_response'])
        best_label = search_labels.get(best_st, best_st.upper())
        best_time = results[best_st]['avg_response']
        
        # Total requests
        total_reqs = sum(r['total_requests'] for r in results.values())
        total_failures = sum(r['failures'] for r in results.values())
        avg_failure_rate = (total_failures / total_reqs * 100) if total_reqs > 0 else 0
        
        html += f"""
            <div class="summary-card">
                <h3>Best Performer</h3>
                <div class="value">{best_label}</div>
                <div class="unit">{best_time:.0f} ms avg</div>
            </div>
            <div class="summary-card">
                <h3>Total Requests</h3>
                <div class="value">{total_reqs:,}</div>
                <div class="unit">all tests</div>
            </div>
            <div class="summary-card">
                <h3>Overall Failure Rate</h3>
                <div class="value">{avg_failure_rate:.2f}%</div>
                <div class="unit">{total_failures} failures</div>
            </div>
        """
    
    html += """
        </div>

        <h2>📈 Response Time Comparison</h2>
        <div class="chart-container">
            <canvas id="responseTimeChart"></canvas>
        </div>

        <h2>⚡ Throughput (Requests/Second)</h2>
        <div class="chart-container">
            <canvas id="throughputChart"></canvas>
        </div>

        <h2>📉 Response Time Percentiles</h2>
        <div class="chart-container">
            <canvas id="percentilesChart"></canvas>
        </div>

        <h2>❌ Failure Rate</h2>
        <div class="chart-container">
            <canvas id="failureChart"></canvas>
        </div>

        <h2>📋 Detailed Metrics</h2>
        <table>
            <thead>
                <tr>
                    <th>Search Type</th>
                    <th>Requests</th>
                    <th>Failures</th>
                    <th>Avg (ms)</th>
                    <th>Median (ms)</th>
                    <th>95% (ms)</th>
                    <th>99% (ms)</th>
                    <th>RPS</th>
                    <th>Failure %</th>
                </tr>
            </thead>
            <tbody>
"""
    
    # Add table rows
    for search_type in search_types:
        if search_type not in results:
            continue
        
        r = results[search_type]
        label = search_labels.get(search_type, search_type.upper())
        
        # Color code failure rate
        failure_class = 'metric-good' if r['failure_rate'] < 1 else ('metric-warning' if r['failure_rate'] < 5 else 'metric-bad')
        
        html += f"""
                <tr>
                    <td><strong>{label}</strong></td>
                    <td>{r['total_requests']:,}</td>
                    <td>{r['failures']:,}</td>
                    <td>{r['avg_response']:.0f}</td>
                    <td>{r['median_response']:.0f}</td>
                    <td>{r['p95_response']:.0f}</td>
                    <td>{r['p99_response']:.0f}</td>
                    <td>{r['rps']:.2f}</td>
                    <td class="{failure_class}">{r['failure_rate']:.2f}%</td>
                </tr>
"""
    
    html += """
            </tbody>
        </table>

        <h2>💡 Key Insights</h2>
        <div class="info-box">
"""
    
    # Generate insights
    if results:
        # Best and worst performers
        best_st = min(results.keys(), key=lambda x: results[x]['avg_response'])
        worst_st = max(results.keys(), key=lambda x: results[x]['avg_response'])
        best_label = search_labels.get(best_st, best_st.upper())
        worst_label = search_labels.get(worst_st, worst_st.upper())
        best_time = results[best_st]['avg_response']
        worst_time = results[worst_st]['avg_response']
        diff_pct = ((worst_time - best_time) / best_time) * 100
        
        # Highest throughput
        highest_rps_st = max(results.keys(), key=lambda x: results[x]['rps'])
        highest_rps_label = search_labels.get(highest_rps_st, highest_rps_st.upper())
        highest_rps = results[highest_rps_st]['rps']
        
        html += f"""
            <strong>🏆 Fastest:</strong> {best_label} with {best_time:.0f}ms average response time<br>
            <strong>🐌 Slowest:</strong> {worst_label} with {worst_time:.0f}ms average response time ({diff_pct:.1f}% slower)<br>
            <strong>⚡ Highest Throughput:</strong> {highest_rps_label} with {highest_rps:.2f} requests/second<br>
            <strong>📊 Parallel Execution:</strong> Each test sends 9 simultaneous HTTP requests (one per collection)<br>
            <strong>⏱️ Total Time:</strong> Time = max(slowest collection response) + HTTP overhead
        """
    
    html += """
        </div>

        <div class="footer">
            Generated by Parallel Collection Testing Report Generator | 
            Weaviate Performance Testing Suite
        </div>
    </div>

    <script>
        // Color palette
        const colors = {
            blue: 'rgba(52, 152, 219, 0.8)',
            green: 'rgba(46, 204, 113, 0.8)',
            orange: 'rgba(230, 126, 34, 0.8)',
            red: 'rgba(231, 76, 60, 0.8)',
            purple: 'rgba(155, 89, 182, 0.8)',
        };

        const borderColors = {
            blue: 'rgba(52, 152, 219, 1)',
            green: 'rgba(46, 204, 113, 1)',
            orange: 'rgba(230, 126, 34, 1)',
            red: 'rgba(231, 76, 60, 1)',
            purple: 'rgba(155, 89, 182, 1)',
        };

        // Data
        const labels = """ + json.dumps(labels) + """;
        const avgTimes = """ + json.dumps(avg_times) + """;
        const medianTimes = """ + json.dumps(median_times) + """;
        const p95Times = """ + json.dumps(p95_times) + """;
        const p99Times = """ + json.dumps(p99_times) + """;
        const rpsValues = """ + json.dumps(rps_values) + """;
        const failureRates = """ + json.dumps(failure_rates) + """;

        // Response Time Chart
        new Chart(document.getElementById('responseTimeChart'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Average',
                        data: avgTimes,
                        backgroundColor: colors.blue,
                        borderColor: borderColors.blue,
                        borderWidth: 2
                    },
                    {
                        label: 'Median',
                        data: medianTimes,
                        backgroundColor: colors.green,
                        borderColor: borderColors.green,
                        borderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Average vs Median Response Time (ms)',
                        font: { size: 16 }
                    },
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Response Time (ms)'
                        }
                    }
                }
            }
        });

        // Throughput Chart
        new Chart(document.getElementById('throughputChart'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Requests/Second',
                    data: rpsValues,
                    backgroundColor: colors.green,
                    borderColor: borderColors.green,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Throughput Comparison',
                        font: { size: 16 }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Requests/Second'
                        }
                    }
                }
            }
        });

        // Percentiles Chart
        new Chart(document.getElementById('percentilesChart'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Average',
                        data: avgTimes,
                        borderColor: borderColors.blue,
                        backgroundColor: colors.blue,
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: 'Median (50%)',
                        data: medianTimes,
                        borderColor: borderColors.green,
                        backgroundColor: colors.green,
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: '95th Percentile',
                        data: p95Times,
                        borderColor: borderColors.orange,
                        backgroundColor: colors.orange,
                        fill: false,
                        tension: 0.1
                    },
                    {
                        label: '99th Percentile',
                        data: p99Times,
                        borderColor: borderColors.red,
                        backgroundColor: colors.red,
                        fill: false,
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Response Time Distribution',
                        font: { size: 16 }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Response Time (ms)'
                        }
                    }
                }
            }
        });

        // Failure Rate Chart
        new Chart(document.getElementById('failureChart'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Failure Rate (%)',
                    data: failureRates,
                    backgroundColor: colors.red,
                    borderColor: borderColors.red,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Failure Rate Comparison',
                        font: { size: 16 }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Failure Rate (%)'
                        }
                    }
                }
            }
        });
    </script>
</body>
</html>
"""
    
    return html


def main():
    """Main function"""
    print("=" * 70)
    print("📊 Parallel Collection Testing Report Generator")
    print("=" * 70)
    
    # Check if results folder specified
    if len(sys.argv) > 1:
        results_folder = sys.argv[1]
    else:
        # Find latest results folder
        results_folder = find_latest_results_folder()
        if not results_folder:
            print("\n❌ No results folders found!")
            print("Usage: python generate_parallel_report.py [results_folder]")
            print("Example: python generate_parallel_report.py results_20251025_103726")
            return 1
    
    # Scan results (scan_parallel_results handles path resolution)
    results = scan_parallel_results(results_folder)
    
    if not results:
        print("\n❌ No test results found in the folder!")
        return 1
    
    if not results:
        print("\n❌ No test results found in the folder!")
        return 1
    
    print(f"\n✅ Found results for {len(results)} search types")
    
    # Generate report (use original folder name for display)
    print("\n📝 Generating HTML report...")
    display_folder = os.path.basename(results_folder) if os.path.isabs(results_folder) or '/' in results_folder else results_folder
    html = generate_html_report(results, display_folder)
    
    # Save report to reports directory
    reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports', 'parallel_testing')
    os.makedirs(reports_dir, exist_ok=True)
    
    # Use results folder name for report filename
    report_filename = f'parallel_collection_report_{display_folder}.html'
    output_file = os.path.join(reports_dir, report_filename)
    
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"\n✅ Report generated: {output_file}")
    print(f"\n🌐 Open in browser: file://{os.path.abspath(output_file)}")
    print("=" * 70)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

