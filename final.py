#importing libraries 
#used yfinance AKA Yahoo finance API or fetching the stocks data in real time

import tkinter as tk#for the gui
from tkinter import ttk, messagebox#for windows initialisatin and pop up boxes
import yfinance as yf#for getting the data of the stock data
import matplotlib.pyplot as plt#for plotting the graph\/trends
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd#data manipulation and analysis of the data
import threading#used for fetching and updating the gui by running in the backgrund, helps us not to run the code over and over
from datetime import datetime, timedelta#hndles the timstamps and scheduling the updates
import time

#crwating a class named STockMarketVisualizer
class StockMarketVisualizer:
    #the class initialisatin
    def __init__(self,root):#self is for initialising the instance of he clas and thr rot is the main window we work like root = tk.Tk()
        self.root = root #initialising a variable wiht the root value
        #window title and geometry initialize
        self.root.title("Real-Time Stock Market Visualizer")
        self.root.geometry("1200x800")

        #variables we need 
        self.stock_symbols = []#stores the stocks symbols
        #declaring a list of dictionaries
        self.tracked_stocks = []#keeps starck of the stocks that were added
        self.alerts = {}#for alert stocks
        self.update_interval = 60 #seconds
        self.historical_days = 30#for fetching the data for csv

        #setup the gui
        self.setup_gui()

        #start the background threds which update he data in real time
        self.running = True
        self.update_thread =threading.Thread(target=self.update_stock_data,daemon=True)
        #target = update_stock_data returns that function
        #daemon Indicates that the thread is a "daemon thread"
        self.update_thread.start()

        #close holder
        self.root.protocol("WM_DELETE_WINDOW",self.on_closing)
        #The  protocol in Tkinter intercepts the window closing event, and  is a method you define elsewhere in your code to handle this event
    
    #gui_setup functin
    def setup_gui(self):
        #declaring the main frame
        control_frame = ttk.Frame(self.root,padding="5")
        control_frame.pack(side=tk.LEFT, fill=tk.Y)
        #positioning the frame to its left

        #the display frame
        display_frame  = ttk.Frame(self.root, padding="5")
        display_frame.pack(side=tk.RIGHT,fill=tk.BOTH,expand=True)

        #control panel
        ttk.Label(control_frame,text="Stock Symbol:").pack(pady=5)
        self.symbol_entry = ttk.Entry(control_frame)
        self.symbol_entry.pack(pady=5)

        #buttoon for adding the stck
        ttk.Button(control_frame,text="Add Stock",command=self.add_stock).pack(pady=3)
        
        #track the stocks lists
        ttk.Label(control_frame,text="Tracked Stocks:").pack(pady=3)
        self.stock_listbox = tk.Listbox(control_frame,height=5,selectmode=tk.SINGLE)
        self.stock_listbox.pack(padx=3)
        ttk.Button(control_frame,text="Remove selected stock",command=self.remove_stock).pack(pady=3)
        #Alarm button and settings
        ttk.Label(control_frame,text="Set Alarm:").pack(pady=3)

        ttk.Label(control_frame,text="Price").pack(pady=3)
        self.alert_price_entry = ttk.Entry(control_frame)
        self.alert_price_entry.pack(pady=3)

        ttk.Label(control_frame,text="Condition").pack(pady=3)
        self.alert_condition = ttk.Combobox(control_frame,values=["Above","Below"])
        self.alert_condition.pack(pady=3)
        self.alert_condition.current(0)

        ttk.Button(control_frame,text="Set Alert",command=self.set_alert).pack(pady=3)

        #Historical data settings
        ttk.Label(control_frame,text="Historical days:").pack(pady=3)
        self.historical_days_entry = ttk.Entry(control_frame)
        self.historical_days_entry.insert(0,str(self.historical_days))
        self.historical_days_entry.pack(pady=3)

        #adding a button for the history update
        ttk.Button(control_frame,text="Update days",command=self.update_historical_days).pack(pady=3)
        #export csv button 
        ttk.Button(control_frame,text="Export to CSV",command=self.export_to_csv).pack(pady=3)

        #update interval
        ttk.Label(control_frame,text="Update Interval (sec): ").pack(pady=3)
        self.updated_interval_entry = ttk.Entry(control_frame)
        self.updated_interval_entry.insert(0,str(self.update_interval))
        self.updated_interval_entry.pack(pady=3)
        ttk.Button(control_frame,text="Apply Interval",command=self.update_interval_setting).pack(pady=3)
        #current Prize display
        self.prices_text = tk.Text(display_frame,height=5,state=tk.DISABLED)
        self.prices_text.pack(fill=tk.X)

        #Alerts display
        ttk.Label(display_frame, text="Active alerts:").pack(pady=3)
        self.alerts_texts = tk.Text(display_frame,height=5,state = tk.DISABLED)
        self.alerts_texts.pack(fill=tk.X,pady=3)

        #Dusplay the graph or he trend of the stocks
        self.figure = plt.Figure(figsize=(10,6),dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure,master=display_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH,expand=True)


    #the add stock function
    def add_stock(self):
        symbol = self.symbol_entry.get().strip().upper()#making the symbol uppercase
        if symbol and symbol not in self.stock_symbols:
            self.stock_symbols.append(symbol)#adds to the list of stock symbols
            self.stock_listbox.insert(tk.END,symbol)#adds to the listbox 
            self.symbol_entry.delete(0,tk.END)#delete the text in the input box
            self.update_display()

    #function for removing the stocks
    def remove_stock(self):
        selection = self.stock_listbox.curselection()#gets the thing we selected in the listbox
        if selection:#if selection exixts
            index = selection[0]
            symbol = self.stock_listbox.get(index)#gets the index of the listbox item
            self.stock_symbols.remove(symbol)#removes the symbol
            self.stock_listbox.delete(index)#deletes the item at that index

            #Remove if there are any alerts for this stock
            if symbol in self.alerts:
                del self.alerts[symbol]

            self.update_display()

    #setting an alert message if the stock price reaches the amount we gave
    def set_alert(self):
        selection = self.stock_listbox.curselection()
        if not selection:
            messagebox.showerror("Error","Please select a stock from the list")
            return
        
        try:
            price = float(self.alert_price_entry.get())#gets the price
            condition = self.alert_condition.get()#gets condition
        except ValueError:
            messagebox.showerror("Error","please enter a valid price")
            return
        
        index = selection[0]
        symbol = self.stock_listbox.get(index)
        self.alerts[symbol] = {"Price":price,"Condition":condition}#storing this in the json
        print("ALerts:",self.alerts)
        self.update_alert_display()
        messagebox.showinfo("Success",f"Alert set for {symbol} at price {condition}{price}")

    #function for updating the graph based on interval lets say like 60sseconds time span
    def update_interval_setting(self):
        try:
            interval = int(self.updated_interval_entry.get())#gets the interval we declare above
            if interval<10:
                messagebox.showerror("Error","Interval must be at least 10 seconds")
            else:
                self.update_interval = interval
                messagebox.showinfo("Success",f"Update interval set to {interval} seconds")
        except ValueError:
            messagebox.showerror("Error","Please enter a valid number")
    
    #function to fetch data based on the symbol provides
    def fetch_stock_data(self,symbol):
        try:
            #gets real time data
            stock = yf.Ticker(symbol)
            hist = stock.history(period=f"{self.historical_days}d")
            #gets the data of previous history

            current_data = stock.history(period="1d")
            if not current_data.empty:
                current_price = current_data['Close'].iloc[-1]
            else:
                current_price = hist['Close'].iloc[-1] if not hist.empty() else 0
            
            #returns a dict
            return {
                "symbol":symbol,
                "history":hist,
                "current_price":current_price,
                "last_updated":datetime.now()
            }
        
        #exception if unable to fetcht the data
        except Exception as e:
            print(f"Error fetching the data for {symbol}:{e}")
            return None

    #function for getting or fetching the app data and storing ti
    def update_stock_data(self):
        while self.running:#while threading running
            if self.stock_symbols:#if existed symbols
                updated_data = []#for storing data which was updates
                for symbol in self.stock_symbols:
                    data = self.fetch_stock_data(symbol)#fetching the stock data based on the symbol
                    if data:
                        updated_data.append(data)
                
                self.tracked_stocks = updated_data#gets the updated data to the tracked list of dicts
                self.root.after(0,self.update_display)
                self.check_alerts()#finally checks any alerts after getting data
            
            time.sleep(self.update_interval)
    
    #function for updating the display
    def update_display(self):
        if not self.tracked_stocks:
            return
        
        #clear previous plots
        self.ax.clear()

        #plots the historical data of given days
        for stock in self.tracked_stocks:
            if not stock['history'].empty:
                self.ax.plot(stock['history'].index,stock['history']['Close'],label=stock['symbol'])
                #self.ax is a matplotlib Axes object, used for plotting on a specific graph.
                #stock['history'].index is likely the date/time values (x-axis).
                #stock['history']['Close'] is the stock’s closing price over time (y-axis).
                #label=stock['symbol'] assigns a label to the line for this stock (used in the legend).

        #giving graph details
        self.ax.set_title("Stock Price History")
        self.ax.set_xlabel("Date")
        self.ax.set_ylabel("Price($)")
        self.ax.legend()#creates a small box on the corner for mentioning the name
        self.ax.grid(True)

        #format x-axis dates
        self.figure.autofmt_xdate()#formats the date which will be on the x axis
        self.canvas.draw()#refresh the plot on the screen

        #update the current price display
        self.prices_text.config(state=tk.NORMAL)
        self.prices_text.delete(1.0,tk.END)

        #heading for the text box to show the alert stocks price and symbols
        header = f"{'Symbol':<10}{'Price':<15}{'Last Updated':<20}\n"
        self.prices_text.insert(tk.END,header)
        self.prices_text.insert(tk.END,"-"*len(header)+"\n")

        #traverse through all the stocks and adding a new line in the text box
        for stock in self.tracked_stocks:
            line = f"{stock['symbol']:<10}{stock['current_price']:<15.2f}{stock['last_updated'].strftime('%Y-%m-%d %H-%M-%S'):<20}\n"
            self.prices_text.insert(tk.END,line)

        self.prices_text.config(state=tk.DISABLED)

        #updates the alert display
        self.update_alert_display()

    #function for the alert update display
    def update_alert_display(self):
        self.alerts_texts.config(state=tk.NORMAL)#makes the alert text editable
        self.alerts_texts.delete(1.0,tk.END)

        if not self.alerts:
            self.alerts_texts.insert(tk.END,"No active alerts")
        else:
            header = f"{'Symbol':<10}{'Condition':<10}{'Price':<15}{'Status':<10}\n"
            self.alerts_texts.insert(tk.END,header)
            self.alerts_texts.insert(tk.END,"-"*len(header)+"\n")

            for symbol,alert in self.alerts.items():
                #find currentprice for this stock
                current_price = None
                for stock in self.tracked_stocks:
                    if stock['symbol']==symbol:
                        current_price = stock['current_price']
                        break
                if current_price is not None:
                    condition_met = (alert['Condition']=="Above" and current_price>alert['Price'])or \
                        (alert['Condition']=="Below" and current_price<alert['Price']) 
                    #for the alert condition checking and meet

                    status = "Triggered " if condition_met else "Watching"

                    line = f"{symbol:<10}{alert['Condition']:<10}{alert['Price']:<15.2f}{status:<10}\n"
                    self.alerts_texts.insert(tk.END,line)#adding the alert line
        
        #making the alerts text not editable again after completeing
        self.alerts_texts.config(state=tk.DISABLED)

    ##function for cheking the alerts and alerting us
    def check_alerts(self):
        for symbol,alert in self.alerts.items():

            #find the current price for the current stock
            current_price = None
            for stock in self.tracked_stocks:
                if stock['symbol']==symbol:
                    current_price = stock['current_price']
                    break
            
            #if the currrent price is not None we need to show an error box
            if current_price is not None:
                condition_met = (alert['Condition'] == "Above" and current_price > alert['Price']) or \
                              (alert['Condition'] == "Below" and current_price < alert['Price'])

                if condition_met:
                    #if the condition met then an alert message will be triggered and pops a window
                    self.root.after(0,lambda s=symbol,a=alert:messagebox.showwarning(
                        "Alert Triggered",
                        f"{s} price is now {a['Condition']} {a['Price']}\nCurrenr price: {current_price:.2f}"
                    ))

    #function for loading the data and put it in the csv file
    def export_to_csv(self):
        if not self.tracked_stocks:
            messagebox.showerror("Error","no stock data to export")
            return
        
        try:
            all_data = [] #store all he dtaa in one csv file
            for stock in self.tracked_stocks:
                if not stock['history'].empty:
                    df = stock['history'][['Close']].copy()#copies the data of history to the df
                    df['Symbol'] = stock['symbol']
                    all_data.append(df)#finally appends the data to the all_data list

            if not all_data:
                messagebox.showerror("Error","NO historical or previous data available to export")
                return

            combined = pd.concat(all_data)#combines all the data means concatinates it into one which is combined
            filename = f"stock_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"#names for the csv file
            combined.to_csv(filename)#converts to csv with the file name

            messagebox.showinfo("Success",f"Data exported to {filename}")
        except Exception as e:
            messagebox.showerror("Error",f"failed to export data: {e}")
    
    # Add this method to update historical days setting:
    def update_historical_days(self):
        try:
            days = int(self.historical_days_entry.get())
            if days > 0:
                self.historical_days = days
                messagebox.showinfo("Success", f"Historical days set to {days}")
            else:
                messagebox.showerror("Error", "Days must be positive")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number")
    
    #wraps up everything when trying to closse the window mean the threads that are running in the backend some other ensure that the application close perfectly
    def on_closing(self):
        self.running = False
        if self.update_thread.is_alive():
            self.update_thread.join(timeout=1)
        self.root.destroy()


#initialising the class and running it
if __name__ == "__main__":
    root = tk.Tk()#initialize the tkinter window
    app = StockMarketVisualizer(root)#like initialising the constructor
    root.mainloop()#mainloop which runs continuosly until close button was clicked
