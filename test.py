import tkinter as tk

def window():
    tk = Tk.tk()
    tk.title("This is a test window for Antimatter")
    tk.geometry("500x500")

    hello_label = tk.Label(text="Hello World !")
    hello_label.pack(side="top")
    click = tk.Button(text="CLICK ME", command=messagebox.showinfo("",""))
    click.pack(side="top")
    tk.mainloop()
    
if __name__ == "__main__":
    window()
