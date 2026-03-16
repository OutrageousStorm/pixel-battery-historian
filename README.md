# 🔋 Pixel Battery Historian

> Visualize Android battery drain culprits with beautiful charts — powered by ADB `dumpsys` parsing. No root needed.

[![Python](https://img.shields.io/badge/python-3.7+-blue?logo=python)](https://python.org)
[![ADB](https://img.shields.io/badge/requires-ADB-green?logo=android)](https://developer.android.com/tools/releases/platform-tools)
[![No Root](https://img.shields.io/badge/root-not%20required-brightgreen)](.)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Google's official Battery Historian requires Docker and a complex setup. This is the **lightweight alternative** — one Python file, one command, beautiful interactive charts.

---

## ✨ Features

- ⚡ **Wakelock analysis** — which apps are waking up your CPU and draining battery
- 📶 **Network usage** — which apps are constantly phoning home
- 📊 **Interactive charts** — built with Chart.js, dark theme
- 📄 **Standalone HTML report** — share it, open it offline
- 🔄 **Reset & measure** — reset stats, use phone, capture results
- ⚡ No root, no Docker, no server — pure ADB + Python

---

## 📦 Requirements

- Python 3.7+
- [ADB (Android Platform Tools)](https://developer.android.com/tools/releases/platform-tools)
- USB Debugging enabled on your Android device

---

## 🚀 Quick Start

```bash
git clone https://github.com/OutrageousStorm/pixel-battery-historian
cd pixel-battery-historian

# Connect phone via USB, enable USB Debugging, then:

# Step 1: Reset the stats (start fresh)
python battery_historian.py --reset

# Step 2: Use your phone normally for a while (30 min - few hours)

# Step 3: Capture and visualize
python battery_historian.py --html
```

This opens a beautiful interactive report showing exactly which apps are killing your battery.

---

## 📊 Report Sections

- **Stats overview** — total tracked time, CPU active time, app counts
- **Top Wakelock Holders** — apps that prevent the CPU from sleeping (bar chart)
- **Top Network Users** — apps consuming mobile/WiFi data (stacked bar chart)
- **Wakelock Detail Table** — full list with visual impact bars
- **Network Detail Table** — upload/download breakdown per app

---

## 🔧 Usage

```bash
# Capture from connected device, generate HTML
python battery_historian.py --html

# Specify output file
python battery_historian.py --html --output my_report.html

# Target specific device (if multiple connected)
python battery_historian.py --device R3CN80XXXXX

# Reset battery stats counter
python battery_historian.py --reset
```

---

## 💡 Tips

- For the most accurate results, reset stats, charge to 100%, then use your phone unplugged for several hours before capturing.
- Wakelocks are the #1 battery drain cause — any app holding a wakelock prevents your CPU from deep sleeping.
- Background network activity on apps you rarely open is a red flag.

---

## 🤝 Contributing

Ideas welcome:
- Timeline chart of battery level over time
- Historical comparison between captures
- Alarm wakeup analysis
- GPS/sensor usage breakdown

---

## 📜 License

MIT

---

*Inspired by Google's Battery Historian but without the Docker overhead.*
