"""
Hussain's Cafe — POS System (GUI)
Pure Python 3 + Tkinter. No external dependencies.

Data is stored in CSV files next to this script:
    orders.csv       one row per item per order
    daily_sales.csv  one row per day (running totals)
    receipts/        a .txt receipt per order
"""

import csv
import os
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

# ── Config ─────────────────────────────────────────────────────────────────────
CAFE_NAME = "Hussain's Cafe"
CURRENCY = "PKR"
TAX_RATE = 0.10
SERVICE_CHG = 0.05

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ORDERS_FILE = os.path.join(APP_DIR, "orders.csv")
SALES_FILE = os.path.join(APP_DIR, "daily_sales.csv")
RECEIPTS_DIR = os.path.join(APP_DIR, "receipts")

ORDER_HEADER = ["Order ID", "Date", "Time", "Table", "Item", "Qty",
                "Unit Price", "Subtotal", "Tax", "Service", "Total", "Payment"]
SALES_HEADER = ["Date", "Orders", "Gross Sales", "Tax Collected",
                "Service Charges", "Net Revenue"]

MENU = {
    "Hot Drinks": {
        "1": ("Espresso", 180), "2": ("Americano", 220), "3": ("Cappuccino", 280),
        "4": ("Latte", 300), "5": ("Green Tea", 150), "6": ("Chai", 120),
    },
    "Cold Drinks": {
        "7": ("Cold Coffee", 320), "8": ("Iced Latte", 340),
        "9": ("Lemonade", 200), "10": ("Mango Shake", 280),
    },
    "Snacks": {
        "11": ("Croissant", 250), "12": ("Club Sandwich", 450), "13": ("Pasta", 550),
        "14": ("Garlic Bread", 200), "15": ("Fries", 220),
    },
    "Desserts": {
        "16": ("Brownie", 280), "17": ("Cheesecake", 380), "18": ("Waffle", 420),
    },
}
CATEGORY_COLORS = {
    "Hot Drinks": "#f3e0cf", "Cold Drinks": "#d9ecf2",
    "Snacks": "#f6ecc4", "Desserts": "#f5d9e3",
}

# ── Theme ──────────────────────────────────────────────────────────────────────
BG, CARD = "#faf6f1", "#ffffff"
DARK, DARK2 = "#3e2723", "#5d4037"
ACCENT, ACCENT_D = "#8d5a3b", "#6f4529"
GREEN, RED = "#2e7d32", "#c62828"
FONT, FONT_B = ("Segoe UI", 10), ("Segoe UI", 10, "bold")
FONT_H, FONT_BIG = ("Segoe UI", 18, "bold"), ("Segoe UI", 16, "bold")


# ── Data layer ─────────────────────────────────────────────────────────────────
def money(x):
    return f"{x:,.0f}"


def initialize_files():
    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    for path, header in ((ORDERS_FILE, ORDER_HEADER), (SALES_FILE, SALES_HEADER)):
        if not os.path.exists(path):
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(header)


def read_rows(path):
    """Return data rows (header skipped), ignoring blank lines."""
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            return [r for r in list(csv.reader(f))[1:] if r]
    except FileNotFoundError:
        return []


def next_order_id():
    ids = []
    for r in read_rows(ORDERS_FILE):
        try:
            ids.append(int(r[0]))
        except (ValueError, IndexError):
            pass
    return max(ids) + 1 if ids else 1001


def calc_bill(cart):
    subtotal = sum(i["qty"] * i["price"] for i in cart.values())
    tax = subtotal * TAX_RATE
    service = subtotal * SERVICE_CHG
    return subtotal, tax, service, subtotal + tax + service


def save_order(order_id, date_str, time_str, table, cart, payment):
    subtotal, tax, service, total = calc_bill(cart)
    with open(ORDERS_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for name, i in cart.items():
            w.writerow([order_id, date_str, time_str, f"Table {table}", name,
                        i["qty"], i["price"], i["qty"] * i["price"],
                        round(tax, 2), round(service, 2), round(total, 2), payment])
    update_daily_sales(date_str, subtotal, tax, service, total)


def update_daily_sales(date, subtotal, tax, service, total):
    rows, found = [], False
    try:
        with open(SALES_FILE, "r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["Date"] == date:
                    row["Orders"] = int(row["Orders"]) + 1
                    row["Gross Sales"] = round(float(row["Gross Sales"]) + subtotal, 2)
                    row["Tax Collected"] = round(float(row["Tax Collected"]) + tax, 2)
                    row["Service Charges"] = round(float(row["Service Charges"]) + service, 2)
                    row["Net Revenue"] = round(float(row["Net Revenue"]) + total, 2)
                    found = True
                rows.append(row)
    except FileNotFoundError:
        pass
    if not found:
        rows.append({"Date": date, "Orders": 1, "Gross Sales": round(subtotal, 2),
                     "Tax Collected": round(tax, 2), "Service Charges": round(service, 2),
                     "Net Revenue": round(total, 2)})
    with open(SALES_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SALES_HEADER)
        w.writeheader()
        w.writerows(rows)


def load_orders():
    """Group CSV rows into {order_id: {...}} (insertion order = oldest first)."""
    orders = {}
    for r in read_rows(ORDERS_FILE):
        try:
            oid = r[0]
            o = orders.setdefault(oid, {
                "id": oid, "date": r[1], "time": r[2], "table": r[3], "items": [],
                "tax": float(r[8]), "service": float(r[9]),
                "total": float(r[10]), "payment": r[11]})
            o["items"].append((r[4], int(r[5]), float(r[6])))
        except (ValueError, IndexError):
            continue
    return orders


def load_sales():
    out = []
    for r in read_rows(SALES_FILE):
        try:
            out.append((r[0], int(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])))
        except (ValueError, IndexError):
            continue
    return out


def best_sellers():
    sales = {}
    for o in load_orders().values():
        for name, qty, price in o["items"]:
            s = sales.setdefault(name, [0, 0.0])
            s[0] += qty
            s[1] += qty * price
    return sorted(sales.items(), key=lambda x: (-x[1][0], -x[1][1]))


def build_receipt(order_id, table, date_str, time_str, items, payment,
                  subtotal, tax, service, total, cash=None):
    w = 42
    L = ["=" * w, CAFE_NAME.center(w), f"Order #{order_id}   {table}".center(w),
         f"{date_str}  {time_str}".center(w), "-" * w,
         f"{'Item':<20}{'Qty':>4}{'Price':>8}{'Total':>10}", "-" * w]
    for name, qty, price in items:
        L.append(f"{name[:19]:<20}{qty:>4}{money(price):>8}{money(qty * price):>10}")
    L += ["-" * w,
          f"{'Subtotal':<28}{money(subtotal):>14}",
          f"{f'Tax ({TAX_RATE * 100:.0f}%)':<28}{money(tax):>14}",
          f"{f'Service Charge ({SERVICE_CHG * 100:.0f}%)':<28}{money(service):>14}",
          "-" * w,
          f"{f'TOTAL ({CURRENCY})':<28}{money(total):>14}",
          f"{'Payment':<28}{payment:>14}"]
    if cash is not None:
        L += [f"{'Cash received':<28}{money(cash):>14}",
              f"{'Change':<28}{money(cash - total):>14}"]
    L += ["=" * w, "Thank you for visiting! Come again".center(w), "=" * w]
    return "\n".join(L)


# ── GUI ────────────────────────────────────────────────────────────────────────
class POSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{CAFE_NAME} — POS System")
        self.geometry("1200x740")
        self.minsize(1050, 660)
        self.configure(bg=BG)
        self.cart = {}  # name -> {"qty": int, "price": float}

        self._setup_style()
        self._build_header()
        self._build_tabs()
        self._build_statusbar()
        self.refresh_cart()
        self.update_status()
        self._tick()
        self.bind("<Control-Return>", lambda e: self.place_order())

    # ── Styling ────────────────────────────────────────────────────────────────
    def _setup_style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass
        s.configure(".", font=FONT, background=BG)
        s.configure("TFrame", background=BG)
        s.configure("Card.TFrame", background=CARD)
        s.configure("TLabel", background=BG)
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", padding=(20, 9), font=FONT_B,
                    background="#e8ddd2", foreground=DARK)
        s.map("TNotebook.Tab", background=[("selected", CARD)])
        s.configure("Treeview", rowheight=28, font=FONT, background=CARD,
                    fieldbackground=CARD, borderwidth=0)
        s.configure("Treeview.Heading", font=FONT_B, background=DARK,
                    foreground="white", padding=6)
        s.map("Treeview.Heading", background=[("active", DARK2)])
        s.map("Treeview", background=[("selected", ACCENT)],
              foreground=[("selected", "white")])
        s.configure("TButton", padding=7, font=FONT)
        s.configure("Accent.TButton", font=("Segoe UI", 12, "bold"),
                    background=ACCENT, foreground="white", padding=12)
        s.map("Accent.TButton", background=[("active", ACCENT_D), ("disabled", "#c9bfb6")])
        s.configure("TRadiobutton", background=CARD)
        s.configure("Sub.TLabel", background=CARD)

    def _build_header(self):
        bar = tk.Frame(self, bg=DARK, height=64)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text=f"☕  {CAFE_NAME}", bg=DARK, fg="white",
                 font=FONT_H).pack(side="left", padx=20)
        self.clock = tk.Label(bar, bg=DARK, fg="#d7ccc8", font=FONT)
        self.clock.pack(side="right", padx=20)

    def _build_statusbar(self):
        self.status = tk.Label(self, anchor="w", bg="#e8ddd2", fg=DARK,
                               font=FONT, padx=12, pady=5)
        self.status.pack(fill="x", side="bottom")

    def _tick(self):
        self.clock.config(text=datetime.now().strftime("%A, %d %B %Y   |   %I:%M:%S %p"))
        self.after(1000, self._tick)

    def update_status(self):
        today = datetime.now().strftime("%Y-%m-%d")
        orders, revenue = 0, 0.0
        for d, n, _, _, _, net in load_sales():
            if d == today:
                orders, revenue = n, net
        self.status.config(
            text=f"Today: {orders} order(s)   •   Revenue: {CURRENCY} {money(revenue)}"
                 f"   •   Next order #: {next_order_id()}   •   Ctrl+Enter = place order")

    # ── Tabs ───────────────────────────────────────────────────────────────────
    def _build_tabs(self):
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        self.tab_order = ttk.Frame(self.nb)
        self.tab_menu = ttk.Frame(self.nb)
        self.tab_hist = ttk.Frame(self.nb)
        self.tab_sales = ttk.Frame(self.nb)
        self.tab_best = ttk.Frame(self.nb)
        for t, label in ((self.tab_order, "🧾  New Order"), (self.tab_menu, "📖  Menu"),
                         (self.tab_hist, "🕘  Order History"), (self.tab_sales, "📊  Sales Report"),
                         (self.tab_best, "🏆  Best Sellers")):
            self.nb.add(t, text=label)
        self._build_order_tab()
        self._build_menu_tab()
        self._build_history_tab()
        self._build_sales_tab()
        self._build_best_tab()
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_tab_change(self, _=None):
        cur = self.nb.nametowidget(self.nb.select())
        if cur is self.tab_hist:
            self.load_history()
        elif cur is self.tab_sales:
            self.load_sales_report()
        elif cur is self.tab_best:
            self.load_best()

    # ── New Order tab ──────────────────────────────────────────────────────────
    def _build_order_tab(self):
        tab = self.tab_order
        tab.columnconfigure(0, weight=3)
        tab.columnconfigure(1, weight=2)
        tab.rowconfigure(0, weight=1)

        # Left: menu cards by category
        left = ttk.Frame(tab)
        left.grid(row=0, column=0, sticky="nsew", padx=(8, 6), pady=8)
        cats = ttk.Notebook(left)
        cats.pack(fill="both", expand=True)
        for cat, items in MENU.items():
            page = tk.Frame(cats, bg=CARD)
            cats.add(page, text=cat)
            for c in range(3):
                page.columnconfigure(c, weight=1, uniform="card")
            for idx, (name, price) in enumerate(items.values()):
                self._menu_card(page, name, price, CATEGORY_COLORS[cat]).grid(
                    row=idx // 3, column=idx % 3, padx=8, pady=8, sticky="nsew")
            for r in range((len(items) + 2) // 3):
                page.rowconfigure(r, weight=0)

        # Right: cart & payment
        right = tk.Frame(tab, bg=CARD, highlightbackground="#e0d6cc", highlightthickness=1)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 8), pady=8)
        right.columnconfigure(0, weight=1)

        top = tk.Frame(right, bg=CARD)
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        tk.Label(top, text="Current Order", bg=CARD, fg=DARK, font=FONT_BIG).pack(side="left")
        self.table_var = tk.StringVar(value="1")
        ttk.Spinbox(top, from_=1, to=99, width=4, textvariable=self.table_var,
                    justify="center").pack(side="right")
        tk.Label(top, text="Table:", bg=CARD, font=FONT_B).pack(side="right", padx=6)

        cols = ("item", "qty", "price", "total")
        self.cart_tree = ttk.Treeview(right, columns=cols, show="headings", height=9,
                                      selectmode="browse")
        for c, t, w, a in (("item", "Item", 150, "w"), ("qty", "Qty", 45, "center"),
                           ("price", "Price", 70, "e"), ("total", "Total", 80, "e")):
            self.cart_tree.heading(c, text=t)
            self.cart_tree.column(c, width=w, anchor=a, stretch=(c == "item"))
        self.cart_tree.grid(row=1, column=0, sticky="nsew", padx=12)
        right.rowconfigure(1, weight=1)
        self.cart_tree.bind("<Delete>", lambda e: self.remove_selected())
        self.cart_tree.bind("<Double-1>", lambda e: self.change_qty(1))

        btns = tk.Frame(right, bg=CARD)
        btns.grid(row=2, column=0, sticky="ew", padx=12, pady=6)
        ttk.Button(btns, text="＋", width=4, command=lambda: self.change_qty(1)).pack(side="left")
        ttk.Button(btns, text="－", width=4, command=lambda: self.change_qty(-1)).pack(side="left", padx=4)
        ttk.Button(btns, text="Remove", command=self.remove_selected).pack(side="left")
        ttk.Button(btns, text="Clear All", command=self.clear_cart).pack(side="right")

        tot = tk.Frame(right, bg=CARD)
        tot.grid(row=3, column=0, sticky="ew", padx=12, pady=4)
        tot.columnconfigure(1, weight=1)
        self.lbl_sub, self.lbl_tax, self.lbl_svc = (tk.StringVar() for _ in range(3))
        self.lbl_total = tk.StringVar()
        for r, (txt, var) in enumerate((("Subtotal", self.lbl_sub),
                                        (f"Tax ({TAX_RATE * 100:.0f}%)", self.lbl_tax),
                                        (f"Service ({SERVICE_CHG * 100:.0f}%)", self.lbl_svc))):
            tk.Label(tot, text=txt, bg=CARD).grid(row=r, column=0, sticky="w")
            tk.Label(tot, textvariable=var, bg=CARD).grid(row=r, column=1, sticky="e")
        tk.Label(tot, text="TOTAL", bg=CARD, fg=DARK, font=FONT_BIG).grid(row=3, column=0, sticky="w", pady=(6, 0))
        tk.Label(tot, textvariable=self.lbl_total, bg=CARD, fg=ACCENT,
                 font=FONT_BIG).grid(row=3, column=1, sticky="e", pady=(6, 0))

        pay = tk.Frame(right, bg=CARD)
        pay.grid(row=4, column=0, sticky="ew", padx=12, pady=(8, 2))
        tk.Label(pay, text="Payment:", bg=CARD, font=FONT_B).pack(side="left")
        self.pay_var = tk.StringVar(value="Cash")
        for p in ("Cash", "Card", "Online Transfer"):
            ttk.Radiobutton(pay, text=p, value=p, variable=self.pay_var,
                            command=self._on_pay_change).pack(side="left", padx=6)

        cash = tk.Frame(right, bg=CARD)
        cash.grid(row=5, column=0, sticky="ew", padx=12, pady=2)
        tk.Label(cash, text=f"Cash received ({CURRENCY}):", bg=CARD).pack(side="left")
        self.cash_var = tk.StringVar()
        self.cash_var.trace_add("write", lambda *a: self._update_change())
        self.cash_entry = ttk.Entry(cash, textvariable=self.cash_var, width=10, justify="right")
        self.cash_entry.pack(side="left", padx=6)
        self.change_lbl = tk.Label(cash, text="", bg=CARD, font=FONT_B)
        self.change_lbl.pack(side="left", padx=6)

        ttk.Button(right, text="✔  Place Order", style="Accent.TButton",
                   command=self.place_order).grid(row=6, column=0, sticky="ew", padx=12, pady=12)

    def _menu_card(self, parent, name, price, color):
        card = tk.Frame(parent, bg=color, cursor="hand2", highlightthickness=1,
                        highlightbackground="#e0d6cc")
        n = tk.Label(card, text=name, bg=color, fg=DARK, font=("Segoe UI", 11, "bold"),
                     wraplength=140, pady=14)
        p = tk.Label(card, text=f"{CURRENCY} {money(price)}", bg=color, fg=ACCENT, font=FONT_B, pady=6)
        n.pack(fill="x")
        p.pack(fill="x")
        hover = "#ffffff"

        def enter(_): [w.config(bg=hover) for w in (card, n, p)]
        def leave(_): [w.config(bg=color) for w in (card, n, p)]
        for w in (card, n, p):
            w.bind("<Button-1>", lambda e, nm=name, pr=price: self.add_item(nm, pr))
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)
        return card

    # ── Cart logic ─────────────────────────────────────────────────────────────
    def add_item(self, name, price):
        if name in self.cart:
            self.cart[name]["qty"] += 1
        else:
            self.cart[name] = {"qty": 1, "price": price}
        self.refresh_cart(select=name)

    def _selected(self):
        sel = self.cart_tree.selection()
        return sel[0] if sel else None

    def change_qty(self, delta):
        name = self._selected()
        if not name:
            return
        self.cart[name]["qty"] += delta
        if self.cart[name]["qty"] <= 0:
            del self.cart[name]
            name = None
        self.refresh_cart(select=name)

    def remove_selected(self):
        name = self._selected()
        if name:
            del self.cart[name]
            self.refresh_cart()

    def clear_cart(self):
        if self.cart and messagebox.askyesno("Clear order", "Remove all items from this order?"):
            self.cart.clear()
            self.refresh_cart()

    def refresh_cart(self, select=None):
        self.cart_tree.delete(*self.cart_tree.get_children())
        for name, i in self.cart.items():
            self.cart_tree.insert("", "end", iid=name, values=(
                name, i["qty"], money(i["price"]), money(i["qty"] * i["price"])))
        if select and select in self.cart:
            self.cart_tree.selection_set(select)
        sub, tax, svc, total = calc_bill(self.cart)
        self.lbl_sub.set(f"{CURRENCY} {money(sub)}")
        self.lbl_tax.set(f"{CURRENCY} {money(tax)}")
        self.lbl_svc.set(f"{CURRENCY} {money(svc)}")
        self.lbl_total.set(f"{CURRENCY} {money(total)}")
        self._update_change()

    def _on_pay_change(self):
        is_cash = self.pay_var.get() == "Cash"
        self.cash_entry.config(state="normal" if is_cash else "disabled")
        self._update_change()

    def _update_change(self):
        if self.pay_var.get() != "Cash":
            self.change_lbl.config(text="")
            return
        try:
            cash = float(self.cash_var.get())
        except ValueError:
            self.change_lbl.config(text="")
            return
        total = calc_bill(self.cart)[3]
        if cash >= total:
            self.change_lbl.config(text=f"Change: {money(cash - total)}", fg=GREEN)
        else:
            self.change_lbl.config(text=f"Short: {money(total - cash)}", fg=RED)

    def place_order(self):
        if not self.cart:
            messagebox.showwarning("Empty order", "Add at least one item first.")
            return
        try:
            table = int(self.table_var.get())
            if table <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid table", "Enter a valid table number.")
            return

        payment = self.pay_var.get()
        sub, tax, svc, total = calc_bill(self.cart)
        cash = None
        if payment == "Cash":
            try:
                cash = float(self.cash_var.get())
            except ValueError:
                messagebox.showerror("Cash required", "Enter the cash amount received.")
                return
            if cash < total:
                messagebox.showerror("Insufficient cash",
                                     f"Total is {CURRENCY} {money(total)}.")
                return

        order_id = next_order_id()
        now = datetime.now()
        date_str, time_str = now.strftime("%Y-%m-%d"), now.strftime("%I:%M %p")
        try:
            save_order(order_id, date_str, time_str, table, self.cart, payment)
        except PermissionError:
            messagebox.showerror("Save failed",
                                 "Could not write to the CSV files. Close them in Excel and try again.")
            return

        items = [(n, i["qty"], i["price"]) for n, i in self.cart.items()]
        receipt = build_receipt(order_id, f"Table {table}", date_str, time_str, items,
                                payment, sub, tax, svc, total, cash)
        path = os.path.join(RECEIPTS_DIR, f"receipt_{order_id}.txt")
        os.makedirs(RECEIPTS_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(receipt)

        self.cart.clear()
        self.cash_var.set("")
        self.refresh_cart()
        self.update_status()
        self.show_receipt(receipt, path)

    # ── Receipt window ─────────────────────────────────────────────────────────
    def show_receipt(self, text, path):
        win = tk.Toplevel(self)
        win.title("Receipt")
        win.configure(bg=BG)
        win.transient(self)
        txt = tk.Text(win, font=("Courier New", 10), width=44,
                      height=text.count("\n") + 2, bg="white", relief="flat", padx=10, pady=10)
        txt.insert("1.0", text)
        txt.config(state="disabled")
        txt.pack(padx=14, pady=(14, 8))
        row = ttk.Frame(win)
        row.pack(pady=(0, 14))

        def save_as():
            dest = filedialog.asksaveasfilename(defaultextension=".txt",
                                                initialfile=os.path.basename(path),
                                                filetypes=[("Text", "*.txt")])
            if dest:
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(text)

        def do_print():
            try:
                if sys.platform.startswith("win"):
                    os.startfile(path, "print")
                else:
                    subprocess.run(["lp", path], check=True)
            except Exception:
                messagebox.showinfo("Print", f"Could not print automatically.\nReceipt saved at:\n{path}")

        ttk.Button(row, text="Print", command=do_print).pack(side="left", padx=4)
        ttk.Button(row, text="Save As…", command=save_as).pack(side="left", padx=4)
        ttk.Button(row, text="Close", command=win.destroy).pack(side="left", padx=4)
        win.grab_set()

    # ── Menu tab ───────────────────────────────────────────────────────────────
    def _build_menu_tab(self):
        tree = ttk.Treeview(self.tab_menu, columns=("id", "name", "price"), show="tree headings")
        tree.heading("#0", text="Category")
        tree.heading("id", text="ID")
        tree.heading("name", text="Item")
        tree.heading("price", text=f"Price ({CURRENCY})")
        tree.column("#0", width=200)
        tree.column("id", width=70, anchor="center")
        tree.column("name", width=300)
        tree.column("price", width=120, anchor="e")
        for cat, items in MENU.items():
            parent = tree.insert("", "end", text=cat, open=True)
            for iid, (name, price) in items.items():
                tree.insert(parent, "end", values=(iid, name, money(price)))
        tree.pack(fill="both", expand=True, padx=8, pady=8)

    # ── History tab ────────────────────────────────────────────────────────────
    def _build_history_tab(self):
        bar = ttk.Frame(self.tab_hist)
        bar.pack(fill="x", padx=8, pady=8)
        ttk.Label(bar, text="Search:", font=FONT_B).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.load_history())
        ttk.Entry(bar, textvariable=self.search_var, width=30).pack(side="left", padx=8)
        ttk.Button(bar, text="View Receipt", command=self.view_selected_receipt).pack(side="right")
        ttk.Button(bar, text="Refresh", command=self.load_history).pack(side="right", padx=6)

        cols = ("id", "date", "time", "table", "items", "total", "pay")
        self.hist_tree = ttk.Treeview(self.tab_hist, columns=cols, show="headings")
        for c, t, w, a in (("id", "Order", 70, "center"), ("date", "Date", 100, "center"),
                           ("time", "Time", 90, "center"), ("table", "Table", 80, "center"),
                           ("items", "Items", 400, "w"), ("total", f"Total ({CURRENCY})", 110, "e"),
                           ("pay", "Payment", 120, "center")):
            self.hist_tree.heading(c, text=t)
            self.hist_tree.column(c, width=w, anchor=a)
        sb = ttk.Scrollbar(self.tab_hist, command=self.hist_tree.yview)
        self.hist_tree.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", pady=(0, 8))
        self.hist_tree.pack(fill="both", expand=True, padx=(8, 0), pady=(0, 8))
        self.hist_tree.bind("<Double-1>", lambda e: self.view_selected_receipt())
        self.hist_orders = {}

    def load_history(self):
        self.hist_orders = load_orders()
        q = self.search_var.get().strip().lower()
        self.hist_tree.delete(*self.hist_tree.get_children())
        for oid, o in reversed(list(self.hist_orders.items())):
            items = ", ".join(f"{n} x{qty}" for n, qty, _ in o["items"])
            row = (oid, o["date"], o["time"], o["table"], items, money(o["total"]), o["payment"])
            if q and q not in " ".join(map(str, row)).lower():
                continue
            self.hist_tree.insert("", "end", iid=oid, values=row)

    def view_selected_receipt(self):
        sel = self.hist_tree.selection()
        if not sel:
            messagebox.showinfo("Select an order", "Select an order first.")
            return
        o = self.hist_orders[sel[0]]
        sub = sum(q * p for _, q, p in o["items"])
        text = build_receipt(o["id"], o["table"], o["date"], o["time"], o["items"],
                             o["payment"], sub, o["tax"], o["service"], o["total"])
        path = os.path.join(RECEIPTS_DIR, f"receipt_{o['id']}.txt")
        if not os.path.exists(path):
            os.makedirs(RECEIPTS_DIR, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        self.show_receipt(text, path)

    # ── Sales tab ──────────────────────────────────────────────────────────────
    def _build_sales_tab(self):
        cards = ttk.Frame(self.tab_sales)
        cards.pack(fill="x", padx=8, pady=8)
        self.stat_vars = {}
        for i, key in enumerate(("Today's Orders", "Today's Revenue", "All-Time Revenue")):
            f = tk.Frame(cards, bg=CARD, highlightbackground="#e0d6cc", highlightthickness=1)
            f.grid(row=0, column=i, sticky="ew", padx=6)
            cards.columnconfigure(i, weight=1)
            tk.Label(f, text=key, bg=CARD, fg="#7b6b60", font=FONT).pack(anchor="w", padx=14, pady=(10, 0))
            v = tk.StringVar(value="0")
            tk.Label(f, textvariable=v, bg=CARD, fg=ACCENT, font=FONT_BIG).pack(anchor="w", padx=14, pady=(0, 10))
            self.stat_vars[key] = v

        cols = ("date", "orders", "gross", "tax", "svc", "net")
        self.sales_tree = ttk.Treeview(self.tab_sales, columns=cols, show="headings")
        for c, t, a in (("date", "Date", "center"), ("orders", "Orders", "center"),
                        ("gross", "Gross Sales", "e"), ("tax", "Tax", "e"),
                        ("svc", "Service", "e"), ("net", "Net Revenue", "e")):
            self.sales_tree.heading(c, text=t)
            self.sales_tree.column(c, width=130, anchor=a)
        self.sales_tree.tag_configure("total", background="#e8ddd2", font=FONT_B)
        self.sales_tree.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        tk.Label(self.tab_sales, text=f"All amounts in {CURRENCY}", bg=BG, fg="#7b6b60").pack(anchor="w", padx=12, pady=(0, 8))

    def load_sales_report(self):
        rows = load_sales()
        self.sales_tree.delete(*self.sales_tree.get_children())
        g = [0, 0.0, 0.0, 0.0, 0.0]
        for d, n, gross, tax, svc, net in reversed(rows):
            self.sales_tree.insert("", "end", values=(d, n, money(gross), money(tax), money(svc), money(net)))
        for _, n, gross, tax, svc, net in rows:
            g = [g[0] + n, g[1] + gross, g[2] + tax, g[3] + svc, g[4] + net]
        if rows:
            self.sales_tree.insert("", "end", tags=("total",), values=(
                "TOTAL", g[0], money(g[1]), money(g[2]), money(g[3]), money(g[4])))
        today = datetime.now().strftime("%Y-%m-%d")
        t_orders = t_rev = 0
        for d, n, _, _, _, net in rows:
            if d == today:
                t_orders, t_rev = n, net
        self.stat_vars["Today's Orders"].set(str(t_orders))
        self.stat_vars["Today's Revenue"].set(f"{CURRENCY} {money(t_rev)}")
        self.stat_vars["All-Time Revenue"].set(f"{CURRENCY} {money(g[4])}")

    # ── Best sellers tab ───────────────────────────────────────────────────────
    def _build_best_tab(self):
        self.tab_best.columnconfigure(0, weight=1)
        self.tab_best.columnconfigure(1, weight=1)
        self.tab_best.rowconfigure(0, weight=1)
        cols = ("rank", "item", "qty", "rev")
        self.best_tree = ttk.Treeview(self.tab_best, columns=cols, show="headings")
        for c, t, w, a in (("rank", "Rank", 55, "center"), ("item", "Item", 180, "w"),
                           ("qty", "Qty Sold", 80, "center"), ("rev", f"Revenue ({CURRENCY})", 120, "e")):
            self.best_tree.heading(c, text=t)
            self.best_tree.column(c, width=w, anchor=a)
        self.best_tree.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        self.chart = tk.Canvas(self.tab_best, bg=CARD, highlightthickness=1,
                               highlightbackground="#e0d6cc")
        self.chart.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        self.chart.bind("<Configure>", lambda e: self._draw_chart())
        self.best_data = []

    def load_best(self):
        self.best_data = best_sellers()
        self.best_tree.delete(*self.best_tree.get_children())
        for rank, (name, (qty, rev)) in enumerate(self.best_data, 1):
            self.best_tree.insert("", "end", values=(rank, name, qty, money(rev)))
        self._draw_chart()

    def _draw_chart(self):
        c = self.chart
        c.delete("all")
        data = self.best_data[:8]
        if not data:
            c.create_text(c.winfo_width() / 2, c.winfo_height() / 2,
                          text="No sales yet", fill="#9e8f84", font=FONT)
            return
        w = max(c.winfo_width(), 300)
        c.create_text(16, 18, anchor="w", text="Top items by quantity sold",
                      font=FONT_B, fill=DARK)
        mx = data[0][1][0]
        y = 50
        for name, (qty, _) in data:
            c.create_text(16, y + 12, anchor="w", text=name, font=FONT, fill=DARK)
            bar_w = (w - 250) * qty / mx
            c.create_rectangle(140, y, 140 + bar_w, y + 24, fill=ACCENT, outline="")
            c.create_text(148 + bar_w, y + 12, anchor="w", text=str(qty), font=FONT_B, fill=DARK)
            y += 40


def main():
    initialize_files()
    POSApp().mainloop()


if __name__ == "__main__":
    main()
