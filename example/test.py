import os
import sys
import ctypes
import tkinter as tk
from tkinter import messagebox, scrolledtext

def load_steam_api_dll():
    if hasattr(sys, '_MEIPASS'):
        dll_path = os.path.join(sys._MEIPASS, "steam_api64.dll")
    else:
        dll_path = os.path.join(os.path.dirname(__file__), "steam_api64.dll")
    return ctypes.WinDLL(dll_path)

steam_api = load_steam_api_dll()

import py_steam_net

class SteamApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Steam Client Demo")
        self.geometry("700x460")

        self.client = py_steam_net.PySteamClient()
        self.current_lobby_id = None

        left_frame = tk.Frame(self)
        left_frame.pack(side='left', fill='y', padx=10, pady=10)

        self.status_label = tk.Label(left_frame, text="Is ready? False")
        self.status_label.pack(pady=10)

        btn_init = tk.Button(left_frame, text="Init Client", command=self.init_client)
        btn_init.pack(fill='x')

        btn_deinit = tk.Button(left_frame, text="Deinit Client", command=self.deinit_client)
        btn_deinit.pack(fill='x', pady=10)

        btn_create_lobby = tk.Button(left_frame, text="Create Lobby", command=self.create_lobby)
        btn_create_lobby.pack(fill='x', pady=(10,0))

        self.lobby_id_label = tk.Label(left_frame, text="Lobby ID: None")
        self.lobby_id_label.pack(pady=10)

        btn_copy_lobby_id = tk.Button(left_frame, text="Copy Lobby ID", command=self.copy_lobby_id)
        btn_copy_lobby_id.pack(fill='x')

        tk.Label(left_frame, text="Join Lobby ID:").pack(pady=(20,0))
        self.join_lobby_entry = tk.Entry(left_frame)
        self.join_lobby_entry.pack(fill='x')

        btn_join_lobby = tk.Button(left_frame, text="Join Lobby", command=self.join_lobby)
        btn_join_lobby.pack(fill='x', pady=10)

        btn_leave_lobby = tk.Button(left_frame, text="Leave Lobby", command=self.leave_lobby)
        btn_leave_lobby.pack(fill='x')

        tk.Label(left_frame, text="Lobby Members (Steam IDs):").pack(pady=(10,0))
        self.members_text = tk.Text(left_frame, height=8, state='disabled', width=30)
        self.members_text.pack(fill='both', pady=(0,10))

        right_frame = tk.Frame(self)
        right_frame.pack(side='right', fill='both', expand=True, padx=10, pady=10)

        tk.Label(right_frame, text="Chat:").pack(anchor='w')

        self.chat_text = scrolledtext.ScrolledText(right_frame, state='disabled', height=22)
        self.chat_text.pack(fill='both', expand=True)

        input_frame = tk.Frame(right_frame)
        input_frame.pack(fill='x', pady=(5,0))

        self.chat_entry = tk.Entry(input_frame)
        self.chat_entry.pack(side='left', fill='x', expand=True)

        btn_send = tk.Button(input_frame, text="Send to Lobby", command=self.send_chat_to_all)
        btn_send.pack(side='right', padx=(5,0))

        self.after(10, self.callback_loop)

    def update_status(self):
        ready = self.client.is_ready()
        self.status_label.config(text=f"Is ready? {ready}")

    def init_client(self):
        try:
            self.client.init(480)
            self.update_status()

            def lobby_changed_callback(lobby_id, user_changed, making_change, member_state_change):
                if self.current_lobby_id == lobby_id:
                    self.update_lobby_members()

            self.client.set_lobby_changed_callback(lobby_changed_callback)

            def on_message_received(sender_steam_id, msg_bytes):
                try:
                    msg = msg_bytes.decode('utf-8', errors='replace')
                except Exception:
                    msg = "<Invalid UTF-8 Message>"
                self.append_chat(f"[{sender_steam_id}] {msg}")

            self.client.set_message_recv_callback(on_message_received)

            def on_connection_failed(steam_id, reason):
                messagebox.showerror("Connection Failed", f"Connection failed for {steam_id} {reason}")

            self.client.set_connection_failed_callback(on_connection_failed)

            messagebox.showinfo("Info", "Client initialized!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def create_lobby(self):
        if not self.client.is_ready():
            messagebox.showwarning("Warning", "Client not initialized!")
            return

        def lobby_callback(lobby_id, error=None):
            if lobby_id is not None:
                self.current_lobby_id = lobby_id
                self.lobby_id_label.config(text=f"Lobby ID: {lobby_id}")
                messagebox.showinfo("Lobby Created", f"Lobby created with ID: {lobby_id}")
                self.update_lobby_members()
            else:
                messagebox.showerror("Lobby Creation Failed", error or "Unknown error")

        self.client.create_lobby(2, 4, lobby_callback)

    def join_lobby(self):
        if not self.client.is_ready():
            messagebox.showwarning("Warning", "Client not initialized!")
            return

        lobby_id_str = self.join_lobby_entry.get()
        if not lobby_id_str.isdigit():
            messagebox.showerror("Error", "Invalid Lobby ID. Must be a number.")
            return

        lobby_id = int(lobby_id_str)

        def join_callback(lobby_id, error=None):
            if lobby_id is not None:
                self.current_lobby_id = lobby_id
                self.lobby_id_label.config(text=f"Joined Lobby ID: {lobby_id}")
                messagebox.showinfo("Lobby Joined", f"Successfully joined lobby: {lobby_id}")
                self.update_lobby_members()
            else:
                messagebox.showerror("Join Lobby Failed", error or "Unknown error")

        self.client.join_lobby(lobby_id, join_callback)

    def leave_lobby(self):
        if not self.client.is_ready():
            messagebox.showwarning("Warning", "Client not initialized!")
            return

        if not self.current_lobby_id:
            messagebox.showwarning("Warning", "Not currently in any lobby.")
            return

        self.client.leave_lobby(self.current_lobby_id)
        messagebox.showinfo("Left Lobby", f"Left lobby {self.current_lobby_id}")

        self.current_lobby_id = None
        self.lobby_id_label.config(text="Lobby ID: None")

        self.members_text.config(state='normal')
        self.members_text.delete('1.0', tk.END)
        self.members_text.config(state='disabled')

        self.chat_text.config(state='normal')
        self.chat_text.delete('1.0', tk.END)
        self.chat_text.config(state='disabled')

    def update_lobby_members(self):
        if not self.current_lobby_id:
            return

        try:
            members = self.client.get_lobby_members(self.current_lobby_id)
            members_str = "\n".join(str(mid) for mid in members)

            self.members_text.config(state='normal')
            self.members_text.delete('1.0', tk.END)
            self.members_text.insert(tk.END, members_str)
            self.members_text.config(state='disabled')
        except Exception as e:
            self.members_text.config(state='normal')
            self.members_text.delete('1.0', tk.END)
            self.members_text.insert(tk.END, f"Error: {e}")
            self.members_text.config(state='disabled')

    def send_chat_to_all(self):
        if not self.current_lobby_id:
            messagebox.showwarning("Warning", "You must be in a lobby to send messages.")
            return

        msg = self.chat_entry.get().strip()
        if not msg:
            return

        try:
            my_id = self.client.own_steam_id()
            members = self.client.get_lobby_members(self.current_lobby_id)
            for member_steam_id in members:
                if member_steam_id == my_id:
                    continue
                self.client.send_message_to(member_steam_id, 2, 0, msg.encode('utf-8'))

            self.append_chat(f"[You] {msg}")
            self.chat_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send message: {e}")

    def append_chat(self, text):
        self.chat_text.config(state='normal')
        self.chat_text.insert(tk.END, text + "\n")
        self.chat_text.see(tk.END)
        self.chat_text.config(state='disabled')

    def callback_loop(self):
        if self.client.is_ready():
            self.client.run_callbacks()
            self.client.receive_messages(0, 100)
        self.after(16, self.callback_loop)

    def deinit_client(self):
        self.client.deinit()
        self.current_lobby_id = None
        self.update_status()
        self.lobby_id_label.config(text="Lobby ID: None")

        self.members_text.config(state='normal')
        self.members_text.delete('1.0', tk.END)
        self.members_text.config(state='disabled')

        self.chat_text.config(state='normal')
        self.chat_text.delete('1.0', tk.END)
        self.chat_text.config(state='disabled')

        messagebox.showinfo("Info", "Client deinitialized.")

    def copy_lobby_id(self):
        lobby_id_text = self.lobby_id_label.cget("text")
        parts = lobby_id_text.split(": ")
        if len(parts) == 2 and parts[1] != "None":
            lobby_id = parts[1]
            self.clipboard_clear()
            self.clipboard_append(lobby_id)
            messagebox.showinfo("Copied", f"Lobby ID {lobby_id} copied to clipboard.")
        else:
            messagebox.showwarning("No Lobby ID", "There is no lobby ID to copy.")

if __name__ == "__main__":
    app = SteamApp()
    app.mainloop()
