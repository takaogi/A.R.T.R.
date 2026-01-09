import sys
import tkinter as tk
from src.utils.logger import logger
from src.ui.chat_window import ChatWindow
from src.utils.initializer import initialize_app

def main():
    # Run initialization checks
    initialize_app()
    
    logger.info("Starting A.R.T.R. application...")
    
    root = tk.Tk()
    app = ChatWindow(root)
    
    logger.info("UI Initialized. Entering main loop.")
    try:
        root.mainloop()
    except KeyboardInterrupt:
        logger.info("Application interrupted.")
    except Exception as e:
        logger.exception("Application crashed.")
    finally:
        logger.info("Application exiting.")

if __name__ == "__main__":
    main()
