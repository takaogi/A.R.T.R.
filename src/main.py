import sys
import os
import asyncio
import tkinter as tk
from src.ui.tkinter.app import App

async def main():
    root = App(asyncio.get_event_loop())
    # Start loop logic is inside App._on_update
    
    # We need to run the tkinter update loop via asyncio or vice versa.
    # App._on_update calls self.update() and schedules itself.
    # So we just need to keep asyncio loop running.
    while True:
        try:
            await asyncio.sleep(0.1)
            # Check if window destroyed
            try:
                root.winfo_exists()
            except tk.TclError:
                break
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
