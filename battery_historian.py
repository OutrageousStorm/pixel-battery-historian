#!/usr/bin/env python3
"""
pixel-battery-historian
Parse Android bugreport battery stats and generate an interactive HTML chart.
No root required — uses ADB bugreport.
"""

import subprocess, sys, os, json, re, argparse, zipfile, tempfile
from datetime import datetime

def run_adb(args, device=None):
    cmd = ["adb"]
    if device:
        cmd += ["-s", device]
    cmd += args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return result.stdout

def get_devices():
    output = run_adb(["devices"])
    return [l.split("\t")[0] for l in output.splitlines()[1:] if "\tdevice" in l]

def capture_batterystats(device=None):
    print("📡 Capturing battery stats from device...")
    output = run_adb(["shell", "dumpsys", "batterystats", "--checkin"], device)
    return output

def parse_batterystats(raw):
    """Parse batterystats --checkin output into structured data."""
    data = {
        "wakelock_summary": [],
        "uid_summary": [],
        "sensor_usage": [],
        "network_usage": [],
        "screen_on_time_pct": 0,
        "battery_level_start": 100,
        "battery_level_end": 0,
        "total_realtime_ms": 0,
        "total_uptime_ms": 0,
    }

    uid_map = {}
    wakelock_map = {}

    for line in raw.splitlines():
        parts = line.split(",")
        if len(parts) < 5:
            continue

        record_type = parts[3] if len(parts) > 3 else ""

        # UID mapping
        if record_type == "uid":
            if len(parts) >= 6:
                uid = parts[4]
                pkg = parts[5]
                uid_map[uid] = pkg

        # Wakelock data
        if record_type == "wl" and len(parts) >= 14:
            try:
                uid = parts[1]
                pkg = uid_map.get(uid, f"uid:{uid}")
                full_wl_ms = int(parts[6]) if parts[6].isdigit() else 0
                partial_wl_ms = int(parts[10]) if parts[10].isdigit() else 0
                total_ms = full_wl_ms + partial_wl_ms
                if total_ms > 0:
                    wakelock_map[pkg] = wakelock_map.get(pkg, 0) + total_ms
            except (ValueError, IndexError):
                pass

        # Network usage
        if record_type == "nt" and len(parts) >= 10:
            try:
                uid = parts[1]
                pkg = uid_map.get(uid, f"uid:{uid}")
                rx_bytes = int(parts[6]) if parts[6].isdigit() else 0
                tx_bytes = int(parts[8]) if parts[8].isdigit() else 0
                total_kb = (rx_bytes + tx_bytes) / 1024
                if total_kb > 0:
                    data["network_usage"].append({
                        "package": pkg,
                        "rx_kb": rx_bytes / 1024,
                        "tx_kb": tx_bytes / 1024,
                        "total_kb": total_kb
                    })
            except (ValueError, IndexError):
                pass

        # Battery summary
        if record_type == "bt" and len(parts) >= 10:
            try:
                data["total_realtime_ms"] = int(parts[5])
                data["total_uptime_ms"] = int(parts[6])
            except (ValueError, IndexError):
                pass

    # Convert wakelock map to sorted list
    data["wakelock_summary"] = sorted(
        [{"package": k, "wakelock_ms": v} for k, v in wakelock_map.items()],
        key=lambda x: x["wakelock_ms"], reverse=True
    )[:20]

    # Sort network usage
    data["network_usage"] = sorted(
        data["network_usage"], key=lambda x: x["total_kb"], reverse=True
    )[:20]

    return data

def generate_html(data, output_file="battery_report.html"):
    wakelock_labels = json.dumps([x["package"].split(".")[-1][:20] for x in data["wakelock_summary"][:10]])
    wakelock_values = json.dumps([round(x["wakelock_ms"] / 1000, 1) for x in data["wakelock_summary"][:10]])

    net_labels = json.dumps([x["package"].split(".")[-1][:20] for x in data["network_usage"][:10]])
    net_rx = json.dumps([round(x["rx_kb"], 1) for x in data["network_usage"][:10]])
    net_tx = json.dumps([round(x["tx_kb"], 1) for x in data["network_usage"][:10]])

    total_hr = data["total_realtime_ms"] / 3600000
    uptime_hr = data["total_uptime_ms"] / 3600000

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Battery Historian Report</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0a0a0a; color: #e0e0e0; padding: 2rem; }}
  h1 {{ font-size: 1.8rem; margin-bottom: 0.25rem; }}
  .subtitle {{ color: #666; margin-bottom: 2rem; font-size: 0.9rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }}
  .card {{ background: #141414; border-radius: 12px; padding: 1.5rem; }}
  .card h2 {{ font-size: 1rem; margin-bottom: 1rem; color: #aaa; text-transform: uppercase; letter-spacing: 0.05em; }}
  .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 2rem; }}
  .stat {{ background: #141414; border-radius: 12px; padding: 1.25rem; }}
  .stat .val {{ font-size: 2rem; font-weight: bold; }}
  .stat .lbl {{ font-size: 0.75rem; color: #666; text-transform: uppercase; margin-top: 0.25rem; }}
  canvas {{ max-height: 280px; }}
  .table-wrap {{ overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  th {{ text-align: left; padding: 0.5rem 0.75rem; color: #888; border-bottom: 1px solid #222; font-weight: 500; }}
  td {{ padding: 0.5rem 0.75rem; border-bottom: 1px solid #1a1a1a; font-family: monospace; }}
  tr:hover td {{ background: #1a1a1a; }}
  .bar {{ height: 6px; background: #1e3a5f; border-radius: 3px; }}
  .bar-fill {{ height: 100%; background: linear-gradient(90deg, #3498db, #2ecc71); border-radius: 3px; }}
</style>
</head>
<body>
<h1>🔋 Battery Historian</h1>
<p class="subtitle">Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} · pixel-battery-historian</p>

<div class="stat-grid">
  <div class="stat"><div class="val">{total_hr:.1f}h</div><div class="lbl">Total Time Tracked</div></div>
  <div class="stat"><div class="val">{uptime_hr:.1f}h</div><div class="lbl">CPU Active Time</div></div>
  <div class="stat"><div class="val">{len(data["wakelock_summary"])}</div><div class="lbl">Apps with Wakelocks</div></div>
  <div class="stat"><div class="val">{len(data["network_usage"])}</div><div class="lbl">Apps Using Network</div></div>
</div>

<div class="grid">
  <div class="card">
    <h2>⚡ Top Wakelock Holders</h2>
    <canvas id="wakelockChart"></canvas>
  </div>
  <div class="card">
    <h2>📶 Top Network Users</h2>
    <canvas id="networkChart"></canvas>
  </div>
</div>

<div class="card" style="margin-bottom: 1.5rem">
  <h2>⚡ Wakelock Detail</h2>
  <div class="table-wrap">
    <table>
      <tr><th>App</th><th>Wakelock Time</th><th>Impact</th></tr>
      {''.join(f"""<tr><td>{x["package"]}</td><td>{x["wakelock_ms"]/1000:.1f}s</td>
      <td><div class="bar"><div class="bar-fill" style="width:{min(100, x['wakelock_ms']/max(1,data['wakelock_summary'][0]['wakelock_ms'])*100):.0f}%"></div></div></td></tr>"""
      for x in data["wakelock_summary"])}
    </table>
  </div>
</div>

<div class="card">
  <h2>📶 Network Usage Detail</h2>
  <div class="table-wrap">
    <table>
      <tr><th>App</th><th>Downloaded</th><th>Uploaded</th><th>Total</th></tr>
      {''.join(f"""<tr><td>{x["package"]}</td>
      <td>{x["rx_kb"]:.0f} KB</td><td>{x["tx_kb"]:.0f} KB</td>
      <td>{x["total_kb"]:.0f} KB</td></tr>"""
      for x in data["network_usage"])}
    </table>
  </div>
</div>

<script>
new Chart(document.getElementById('wakelockChart'), {{
  type: 'bar',
  data: {{
    labels: {wakelock_labels},
    datasets: [{{ 
      label: 'Wakelock (seconds)',
      data: {wakelock_values},
      backgroundColor: 'rgba(52, 152, 219, 0.7)',
      borderColor: 'rgba(52, 152, 219, 1)',
      borderWidth: 1,
      borderRadius: 4
    }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ ticks: {{ color: '#888', maxRotation: 45 }}, grid: {{ color: '#1a1a1a' }} }},
      y: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#1a1a1a' }} }}
    }}
  }}
}});

new Chart(document.getElementById('networkChart'), {{
  type: 'bar',
  data: {{
    labels: {net_labels},
    datasets: [
      {{ label: 'Downloaded (KB)', data: {net_rx}, backgroundColor: 'rgba(46, 204, 113, 0.7)', borderRadius: 4 }},
      {{ label: 'Uploaded (KB)', data: {net_tx}, backgroundColor: 'rgba(231, 76, 60, 0.7)', borderRadius: 4 }}
    ]
  }},
  options: {{
    responsive: true, maintainAspectRatio: true,
    plugins: {{ legend: {{ labels: {{ color: '#888' }} }} }},
    scales: {{
      x: {{ ticks: {{ color: '#888', maxRotation: 45 }}, grid: {{ color: '#1a1a1a' }}, stacked: true }},
      y: {{ ticks: {{ color: '#888' }}, grid: {{ color: '#1a1a1a' }}, stacked: true }}
    }}
  }}
}});
</script>
</body>
</html>"""
    with open(output_file, "w") as f:
        f.write(html)
    print(f"📄 Report saved: {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description="🔋 Visualize Android battery drain culprits — no root required",
        epilog="""
Examples:
  python battery_historian.py               # Capture live from connected device
  python battery_historian.py --html        # Also open report in browser
  python battery_historian.py --reset       # Reset battery stats, then capture
        """
    )
    parser.add_argument("--device", "-d", help="Target device serial")
    parser.add_argument("--html", action="store_true", help="Open HTML report after generating")
    parser.add_argument("--output", "-o", default="battery_report.html")
    parser.add_argument("--reset", action="store_true", help="Reset battery stats before capturing")
    args = parser.parse_args()

    devices = get_devices()
    if not devices:
        print("❌ No device connected. Connect via USB and enable USB Debugging.")
        sys.exit(1)

    device = args.device or devices[0]
    
    if args.reset:
        print("🔄 Resetting battery stats...")
        run_adb(["shell", "dumpsys", "batterystats", "--reset"], device)
        print("   Stats reset. Start using your phone, then run again without --reset.")
        sys.exit(0)

    raw = capture_batterystats(device)
    print("📊 Parsing data...")
    data = parse_batterystats(raw)

    print(f"\n{'='*50}")
    print(f"  TOP WAKELOCK HOLDERS")
    print(f"{'='*50}")
    for app in data["wakelock_summary"][:10]:
        secs = app["wakelock_ms"] / 1000
        bar = "█" * min(30, int(secs / max(1, data["wakelock_summary"][0]["wakelock_ms"] / 1000 / 30)))
        print(f"  {app['package']:<40} {secs:>8.1f}s  {bar}")

    print(f"\n{'='*50}")
    print(f"  TOP NETWORK USERS")
    print(f"{'='*50}")
    for app in data["network_usage"][:10]:
        print(f"  {app['package']:<40} {app['total_kb']:>8.0f} KB")

    generate_html(data, args.output)
    
    if args.html:
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(args.output)}")

if __name__ == "__main__":
    main()
