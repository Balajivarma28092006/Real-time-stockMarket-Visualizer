import tkinter as tk
from tkinter import ttk, messagebox
import yfinance as yf
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd
import threading
from datetime import datetime, timedelta
import time

class StockMarketVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Real-Time Stock Market Visualizer")
        self.root.geometry("1200x800")
        
        # Variables
        self.stock_symbols = []
        self.tracked_stocks = []
        self.alerts = {}
        self.update_interval = 60  # seconds
        self.historical_days = 30
        
        # Setup GUI
        self.setup_gui()
        
        # Start background thread for updates
        self.running = True
        self.update_thread = threading.Thread(target=self.update_stock_data, daemon=True)
        self.update_thread.start()
        
        # Close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_gui(self):
        # Main frames
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        display_frame = ttk.Frame(self.root, padding="10")
        display_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Control Panel
        ttk.Label(control_frame, text="Stock Symbol:").pack(pady=5)
        self.symbol_entry = ttk.Entry(control_frame)
        self.symbol_entry.pack(pady=5)
        
        ttk.Button(control_frame, text="Add Stock", command=self.add_stock).pack(pady=5)
        
        # Tracked Stocks List
        ttk.Label(control_frame, text="Tracked Stocks:").pack(pady=5)
        self.stock_listbox = tk.Listbox(control_frame, height=10, selectmode=tk.SINGLE)
        self.stock_listbox.pack(pady=5)
        ttk.Button(control_frame, text="Remove Selected", command=self.remove_stock).pack(pady=5)
        
        # Alert Settings
        ttk.Label(control_frame, text="Set Alert:").pack(pady=5)
        
        ttk.Label(control_frame, text="Price:").pack(pady=2)
        self.alert_price_entry = ttk.Entry(control_frame)
        self.alert_price_entry.pack(pady=2)
        
        ttk.Label(control_frame, text="Condition:").pack(pady=2)
        self.alert_condition = ttk.Combobox(control_frame, values=["Above", "Below"])
        self.alert_condition.pack(pady=2)
        self.alert_condition.current(0)
        
        ttk.Button(control_frame, text="Set Alert", command=self.set_alert).pack(pady=5)
        
        # Historical Data Settings
        ttk.Label(control_frame, text="Historical Days:").pack(pady=5)
        self.historical_days_entry = ttk.Entry(control_frame)
        self.historical_days_entry.insert(0, str(self.historical_days))
        self.historical_days_entry.pack(pady=5)
        
        # Export Button
        ttk.Button(control_frame, text="Export to CSV", command=self.export_to_csv).pack(pady=10)
        
        # Update Interval
        ttk.Label(control_frame, text="Update Interval (sec):").pack(pady=5)
        self.update_interval_entry = ttk.Entry(control_frame)
        self.update_interval_entry.insert(0, str(self.update_interval))
        self.update_interval_entry.pack(pady=5)
        ttk.Button(control_frame, text="Apply Interval", command=self.update_interval_setting).pack(pady=5)
        
        # Display Panel
        self.figure = plt.Figure(figsize=(10, 6), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=display_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Current Prices Display
        self.prices_text = tk.Text(display_frame, height=10, state=tk.DISABLED)
        self.prices_text.pack(fill=tk.X)
        
        # Alerts Display
        ttk.Label(display_frame, text="Active Alerts:").pack(pady=5)
        self.alerts_text = tk.Text(display_frame, height=5, state=tk.DISABLED)
        self.alerts_text.pack(fill=tk.X)
    
    def add_stock(self):
        symbol = self.symbol_entry.get().strip().upper()
        if symbol and symbol not in self.stock_symbols:
            self.stock_symbols.append(symbol)
            self.stock_listbox.insert(tk.END, symbol)
            self.symbol_entry.delete(0, tk.END)
            self.update_display()
    
    def remove_stock(self):
        selection = self.stock_listbox.curselection()
        if selection:
            index = selection[0]
            symbol = self.stock_listbox.get(index)
            self.stock_symbols.remove(symbol)
            self.stock_listbox.delete(index)
            
            # Remove any alerts for this stock
            if symbol in self.alerts:
                del self.alerts[symbol]
            
            self.update_display()
    
    def set_alert(self):
        selection = self.stock_listbox.curselection()
        if not selection:
            messagebox.showerror("Error", "Please select a stock from the list")
            return
            
        try:
            price = float(self.alert_price_entry.get())
            condition = self.alert_condition.get()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid price")
            return
            
        index = selection[0]
        symbol = self.stock_listbox.get(index)
        self.alerts[symbol] = {"price": price, "condition": condition}
        
        self.update_alerts_display()
        messagebox.showinfo("Success", f"Alert set for {symbol} at price {condition} {price}")
    
    def update_interval_setting(self):
        try:
            interval = int(self.update_interval_entry.get())
            if interval < 10:
                messagebox.showerror("Error", "Interval must be at least 10 seconds")
            else:
                self.update_interval = interval
                messagebox.showinfo("Success", f"Update interval set to {interval} seconds")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number")
    
    def fetch_stock_data(self, symbol):
        try:
            # Get real-time data
            stock = yf.Ticker(symbol)
            hist = stock.history(period=f"{self.historical_days}d")
            
            # Get current price
            current_data = stock.history(period="1d")
            if not current_data.empty:
                current_price = current_data['Close'].iloc[-1]
            else:
                current_price = hist['Close'].iloc[-1] if not hist.empty else 0
            
            return {
                "symbol": symbol,
                "history": hist,
                "current_price": current_price,
                "last_updated": datetime.now()
            }
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
    
    def update_stock_data(self):
        while self.running:
            if self.stock_symbols:
                updated_data = []
                for symbol in self.stock_symbols:
                    data = self.fetch_stock_data(symbol)
                    if data:
                        updated_data.append(data)
                
                self.tracked_stocks = updated_data
                self.root.after(0, self.update_display)
                self.check_alerts()
            
            time.sleep(self.update_interval)
    
    def update_display(self):
        if not self.tracked_stocks:
            return
            
        # Clear previous plots
        self.ax.clear()
        
        # Plot historical data
        for stock in self.tracked_stocks:
            if not stock['history'].empty:
                self.ax.plot(stock['history'].index, stock['history']['Close'], label=stock['symbol'])
        
        self.ax.set_title("Stock Price History")
        self.ax.set_xlabel("Date")
        self.ax.set_ylabel("Price ($)")
        self.ax.legend()
        self.ax.grid(True)
        
        # Format x-axis dates
        self.figure.autofmt_xdate()
        self.canvas.draw()
        
        # Update current prices display
        self.prices_text.config(state=tk.NORMAL)
        self.prices_text.delete(1.0, tk.END)
        
        header = f"{'Symbol':<10}{'Price':<15}{'Last Updated':<20}\n"
        self.prices_text.insert(tk.END, header)
        self.prices_text.insert(tk.END, "-" * len(header) + "\n")
        
        for stock in self.tracked_stocks:
            line = f"{stock['symbol']:<10}{stock['current_price']:<15.2f}{stock['last_updated'].strftime('%Y-%m-%d %H:%M:%S'):<20}\n"
            self.prices_text.insert(tk.END, line)
        
        self.prices_text.config(state=tk.DISABLED)
        
        # Update alerts display
        self.update_alerts_display()
    
    def update_alerts_display(self):
        self.alerts_text.config(state=tk.NORMAL)
        self.alerts_text.delete(1.0, tk.END)
        
        if not self.alerts:
            self.alerts_text.insert(tk.END, "No active alerts")
        else:
            header = f"{'Symbol':<10}{'Condition':<10}{'Price':<15}{'Status':<10}\n"
            self.alerts_text.insert(tk.END, header)
            self.alerts_text.insert(tk.END, "-" * len(header) + "\n")
            
            for symbol, alert in self.alerts.items():
                # Find current price for this stock
                current_price = None
                for stock in self.tracked_stocks:
                    if stock['symbol'] == symbol:
                        current_price = stock['current_price']
                        break
                
                if current_price is not None:
                    condition_met = (alert['condition'] == "Above" and current_price > alert['price']) or \
                                  (alert['condition'] == "Below" and current_price < alert['price'])
                    status = "Triggered" if condition_met else "Watching"
                    
                    line = f"{symbol:<10}{alert['condition']:<10}{alert['price']:<15.2f}{status:<10}\n"
                    self.alerts_text.insert(tk.END, line)
        
        self.alerts_text.config(state=tk.DISABLED)
    
    def check_alerts(self):
        for symbol, alert in self.alerts.items():
            # Find current price for this stock
            current_price = None
            for stock in self.tracked_stocks:
                if stock['symbol'] == symbol:
                    current_price = stock['current_price']
                    break
            
            if current_price is not None:
                condition_met = (alert['condition'] == "Above" and current_price > alert['price']) or \
                              (alert['condition'] == "Below" and current_price < alert['price'])
                
                if condition_met:
                    self.root.after(0, lambda s=symbol, a=alert: messagebox.showwarning(
                        "Alert Triggered",
                        f"{s} price is now {a['condition']} {a['price']}\nCurrent price: {current_price:.2f}"
                    ))
    
    def export_to_csv(self):
        if not self.tracked_stocks:
            messagebox.showerror("Error", "No stock data to export")
            return
            
        try:
            # Combine all historical data
            all_data = []
            for stock in self.tracked_stocks:
                if not stock['history'].empty:
                    df = stock['history'][['Close']].copy()
                    df['Symbol'] = stock['symbol']
                    all_data.append(df)
            
            if not all_data:
                messagebox.showerror("Error", "No historical data available to export")
                return
                
            combined = pd.concat(all_data)
            filename = f"stock_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            combined.to_csv(filename)
            
            messagebox.showinfo("Success", f"Data exported to {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export data: {e}")
    
    def on_closing(self):
        self.running = False
        if self.update_thread.is_alive():
            self.update_thread.join(timeout=1)
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = StockMarketVisualizer(root)
    root.mainloop()