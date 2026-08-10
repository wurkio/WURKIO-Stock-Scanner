import tkinter as tk

from .controller import AppController
from .views.modern_window import ModernWindow


def main() -> None:
    root = tk.Tk()
    ModernWindow(root, AppController())
    root.mainloop()


if __name__ == "__main__":
    main()
