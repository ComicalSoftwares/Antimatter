# The main Discord RPC module

import time
from pathlib import Path
from pypresence import Presence
from PyQt6.QtWidgets import QInputDialog, QMessageBox

RPC = None
RPC_START_TIME = time.time()
is_custom = False

def init_discord():
    global RPC, is_custom
    is_custom = False
    try:
        client_id = "1487828344480464957"
        if not RPC:
            for pipe_num in range(10):
                try:
                    RPC = Presence(client_id, pipe=pipe_num)
                    RPC.connect()
                    RPC.update(
                        details="Doing absolutely nothing",
                        start=RPC_START_TIME,
                        large_image="image",
                        large_text="Antimatter",
                    )
                    break
                except Exception:
                    continue
    except Exception as e:
        print(f"Discord RPC Error: {e}")

def update_rpc(filename=None, is_file_path=True):
    global RPC, is_custom, RPC_START_TIME
    if is_custom or not RPC:
        return
    try:
        if filename:
            display_name = Path(filename).name if is_file_path else filename
            details = f"Editing {display_name}"
        else:
            details = "Editing an untitled File"
            
        RPC.update(
            details=details,
            start=RPC_START_TIME,
            large_image="image",
            large_text="Antimatter",
        )
    except Exception as e:
        print(f"Couldn't update Discord RPC: {e}")

def custom():
    global RPC, is_custom, RPC_START_TIME
    is_custom = True
    message, ok = QInputDialog.getText(None, "Custom Discord RPC Status", "Enter the message that you wish to have on your RPC Card")
    if not ok or not message:
        return
    try:
        RPC.update(
            details=message,
            start=RPC_START_TIME,
            large_image="image",
            large_text="Antimatter",
        )
        QMessageBox.information(None, "Complete !", "Done! Go check out your new status :)")
    except Exception as e:
        print(e)        
        QMessageBox.warning(None, "Failed to set RPC status", "Make sure that your Discord client is running and that you are not offline. If your status is less than two letters long then it will not work, just so you know.")