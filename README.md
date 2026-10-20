# ☕ Hussain's Cafe — POS System

A desktop point-of-sale app for a cafe, built with **Python + Tkinter** (no external dependencies).

## Features
- Click-to-add menu cards grouped by category
- Live cart: quantity +/−, remove, clear
- Auto tax (10%) and service charge (5%)
- Cash / Card / Online Transfer, live change calculation
- Printable receipts (auto-saved to `receipts/`)
- Searchable order history with receipt viewer
- Daily sales report with totals
- Best-selling items table and bar chart
- Data stored in simple CSV files (`orders.csv`, `daily_sales.csv`)

## Run
```bash
python pos_gui.py
```
Requires Python 3.8+ (Tkinter ships with Python on Windows/macOS; on Linux: `sudo apt install python3-tk`).

## Customize
Edit `MENU`, `TAX_RATE`, `SERVICE_CHG`, `CAFE_NAME` and `CURRENCY` at the top of `pos_gui.py`.

## Shortcuts
`Ctrl+Enter` place order · `Delete` remove selected item · double-click a cart row to add one more.
