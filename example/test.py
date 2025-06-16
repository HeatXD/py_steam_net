import os
import sys
import ctypes
import tkinter as tk
from tkinter import messagebox, scrolledtext
from PIL import Image, ImageTk, ImageDraw
import random
import json

def load_steam_api_dll():
    if hasattr(sys, '_MEIPASS'):
        dll_path = os.path.join(sys._MEIPASS, "steam_api64.dll")
    else:
        dll_path = os.path.join(os.path.dirname(__file__), "steam_api64.dll")
    try:
        return ctypes.WinDLL(dll_path)
    except OSError as e:
        messagebox.showerror("DLL Error", f"Failed to load steam_api64.dll: {e}\nPlease ensure it's in the correct directory.")
        sys.exit(1)

steam_api = load_steam_api_dll()

import py_steam_net

class SteamApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Steam Client Demo")
        self.geometry("800x700")

        self.client = py_steam_net.PySteamClient()
        self.current_lobby_id = None
        self.peer_colors = {}
        self.my_drawing_color = self._generate_random_color()

        # --- Left Frame: Client and Lobby Management ---
        left_frame = tk.Frame(self)
        left_frame.pack(side='left', fill='y', padx=10, pady=10)

        self.status_label = tk.Label(left_frame, text="Is ready? False")
        self.status_label.pack(pady=10)

        btn_init = tk.Button(left_frame, text="Init Client (App ID: 480)", command=self.init_client)
        btn_init.pack(fill='x')

        btn_deinit = tk.Button(left_frame, text="Deinit Client", command=self.deinit_client)
        btn_deinit.pack(fill='x', pady=10)

        tk.Label(left_frame, text="--- Lobby Operations ---").pack(fill='x', pady=(10,0))
        btn_create_lobby = tk.Button(left_frame, text="Create Lobby (Public, 4 members)", command=self.create_lobby)
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
        self.members_text = scrolledtext.ScrolledText(left_frame, height=5, state='disabled', width=30)
        self.members_text.pack(fill='both', expand=True, pady=(0,10))

        self.my_color_label = tk.Label(left_frame, text=f"Your Color: {self.my_drawing_color}", bg=self.my_drawing_color, fg="white")
        self.my_color_label.pack(fill='x', pady=5)


        # --- Right Frame: Chat, Canvas and Connection Requests ---
        right_frame = tk.Frame(self)
        right_frame.pack(side='right', fill='both', expand=True, padx=10, pady=10)

        tk.Label(right_frame, text="Drawing Canvas:").pack(anchor='w')

        self.canvas_width = 600
        self.canvas_height = 300
        self.drawing_canvas = tk.Canvas(right_frame, bg="white", width=self.canvas_width, height=self.canvas_height, bd=2, relief="groove")
        self.drawing_canvas.pack(pady=5)

        self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.last_x, self.last_y = None, None

        self.drawing_canvas.bind("<Button-1>", self.start_draw)
        self.drawing_canvas.bind("<B1-Motion>", self.draw_line)
        self.drawing_canvas.bind("<ButtonRelease-1>", self.stop_draw)

        btn_clear_canvas = tk.Button(right_frame, text="Clear Canvas", command=self.clear_canvas)
        btn_clear_canvas.pack(pady=5)

        tk.Label(right_frame, text="Chat:").pack(anchor='w', pady=(10,0))
        self.chat_text = scrolledtext.ScrolledText(right_frame, state='disabled', height=10)
        self.chat_text.pack(fill='both', expand=True)

        input_frame = tk.Frame(right_frame)
        input_frame.pack(fill='x', pady=(5,0))

        self.chat_entry = tk.Entry(input_frame)
        self.chat_entry.pack(side='left', fill='x', expand=True)
        self.chat_entry.bind("<Return>", lambda event: self.send_chat_to_all())

        btn_send = tk.Button(input_frame, text="Send to Lobby", command=self.send_chat_to_all)
        btn_send.pack(side='right', padx=(5,0))

        self.after(10, self.callback_loop)

    def _generate_random_color(self):
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        return f'#{r:02x}{g:02x}{b:02x}'

    def update_status(self):
        ready = self.client.is_ready()
        self.status_label.config(text=f"Is ready? {ready}")

    def init_client(self):
        try:
            self.client.init(480)
            self.update_status()
            my_steam_id = self.client.own_steam_id()
            self.peer_colors[my_steam_id] = self.my_drawing_color
            self.my_color_label.config(text=f"Your Color: {self.my_drawing_color}", bg=self.my_drawing_color)


            def lobby_changed_callback(lobby_id, user_changed, making_change, member_state_change):
                if self.current_lobby_id == lobby_id:
                    self.update_lobby_members()
                    self._sync_colors_with_lobby()

            self.client.set_lobby_changed_callback(lobby_changed_callback)

            def on_message_received(sender_steam_id, channel, msg_bytes):
                if channel == 0:
                    msg = msg_bytes.decode('utf-8', errors='ignore')
                    self.append_chat(f"[{sender_steam_id}] {msg}", sender_steam_id)
                elif channel == 1:
                    data = json.loads(msg_bytes.decode('utf-8'))
                    if data.get("type") == "drawing":
                        self.display_received_drawing_segment(sender_steam_id, data["payload"])
                    elif data.get("type") == "color_sync":
                        self.peer_colors[sender_steam_id] = data["payload"]["color"]
                        self.append_chat(f"[{sender_steam_id}] is now drawing in {self.peer_colors[sender_steam_id]}", sender_steam_id)
                    elif data.get("type") == "clear_canvas":
                        self.clear_canvas_remote()
                    elif data.get("type") == "color_sync_request":
                        self._send_color_sync(sender_steam_id, self.my_drawing_color)
                        self.append_chat(f"[System] Sent color to {sender_steam_id} upon request.", self.client.own_steam_id())
                    else:
                        msg = msg_bytes.decode('utf-8')
                        self.append_chat(f"[{sender_steam_id}] {msg}", sender_steam_id)

            self.client.set_message_recv_callback(on_message_received)
            self.client.set_connection_failed_callback(self._on_connection_failed)

            messagebox.showinfo("Info", "Client initialized!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _on_connection_failed(self, steam_id):
        messagebox.showerror("Connection Failed", f"Connection failed for Steam ID: {steam_id}")
        if steam_id in self.peer_colors:
            del self.peer_colors[steam_id]
        self.update_lobby_members()
        self.append_chat(f"[System] Connection with {steam_id} failed.", self.client.own_steam_id())


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
                self._sync_colors_with_lobby()
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

        def join_callback(lobby_id_returned, error=None):
            if lobby_id_returned is not None:
                self.current_lobby_id = lobby_id_returned
                self.lobby_id_label.config(text=f"Joined Lobby ID: {lobby_id_returned}")
                messagebox.showinfo("Lobby Joined", f"Successfully joined lobby: {lobby_id_returned}")
                self.update_lobby_members()
                self._sync_colors_with_lobby()
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
        self.peer_colors.clear()
        my_steam_id = self.client.own_steam_id()
        if my_steam_id != 0:
             self.peer_colors[my_steam_id] = self.my_drawing_color


        self.members_text.config(state='normal')
        self.members_text.delete('1.0', tk.END)
        self.members_text.config(state='disabled')

        self.chat_text.config(state='normal')
        self.chat_text.delete('1.0', tk.END)
        self.chat_text.config(state='disabled')

        self.clear_canvas()
        self.append_chat("[System] You left the lobby.", self.client.own_steam_id())

    def update_lobby_members(self):
        if not self.current_lobby_id:
            self.members_text.config(state='normal')
            self.members_text.delete('1.0', tk.END)
            self.members_text.insert(tk.END, "No lobby active.")
            self.members_text.config(state='disabled')
            return

        try:
            current_members = self.client.get_lobby_members(self.current_lobby_id)
            if not current_members:
                members_str = "No members (yet)."
            else:
                members_display = []
                my_id = self.client.own_steam_id()
                for mid in current_members:
                    if mid not in self.peer_colors and mid != my_id:
                        self._request_color_sync(mid)
                        self.peer_colors[mid] = "#CCCCCC" # Temporary default
                        self.append_chat(f"[System] Requested color from {mid}...", my_id)

                    members_display.append(f"{mid}")
                members_str = "\n".join(members_display)

            self.members_text.config(state='normal')
            self.members_text.delete('1.0', tk.END)
            self.members_text.insert(tk.END, members_str)
            self.members_text.see(tk.END)
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

            self.append_chat(f"[You] {msg}", my_id)
            self.chat_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send message: {e}")

    def append_chat(self, text, steam_id=None):
        self.chat_text.config(state='normal')
        
        start_index = self.chat_text.index(tk.END + "-1c")
        
        self.chat_text.insert(tk.END, text + "\n")

        if steam_id is not None:
            color = self.peer_colors.get(steam_id)
            if color:
                id_string = f"[{steam_id}]"
                id_start_pos = text.find(id_string)
                
                if id_start_pos != -1:
                    tag_name = f"color_{color.replace('#', '')}"
                    self.chat_text.tag_config(tag_name, foreground=color)
                    
                    tag_start_index = f"{start_index}+{id_start_pos}c"
                    tag_end_index = f"{start_index}+{id_start_pos + len(id_string)}c"
                    self.chat_text.tag_add(tag_name, tag_start_index, tag_end_index)

        self.chat_text.see(tk.END)
        self.chat_text.config(state='disabled')

    def callback_loop(self):
        if self.client.is_ready():
            self.client.run_callbacks()
            self.client.receive_messages(0, 100)
            self.client.receive_messages(1, 100)
        self.after(16, self.callback_loop)

    def deinit_client(self):
        self.client.deinit()
        self.current_lobby_id = None
        self.update_status()
        self.lobby_id_label.config(text="Lobby ID: None")
        self.peer_colors.clear()
        self.my_drawing_color = self._generate_random_color()
        self.my_color_label.config(text=f"Your Color: {self.my_drawing_color}", bg=self.my_drawing_color)


        self.members_text.config(state='normal')
        self.members_text.delete('1.0', tk.END)
        self.members_text.insert(tk.END, "Client deinitialized. No members.")
        self.members_text.config(state='disabled')

        self.chat_text.config(state='normal')
        self.chat_text.delete('1.0', tk.END)
        self.chat_text.insert(tk.END, "Client deinitialized. Chat cleared.")
        self.chat_text.config(state='disabled')

        self.clear_canvas()
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

    # --- Color Synchronization Methods ---
    def _send_color_sync(self, target_steam_id, color):
        if not self.client.is_ready():
            return
        message = {
            "type": "color_sync",
            "payload": {"color": color}
        }
        try:
            self.client.send_message_to(target_steam_id, 2, 1, json.dumps(message).encode('utf-8'))
        except Exception as e:
            print(f"Error sending color sync to {target_steam_id}: {e}")

    def _request_color_sync(self, target_steam_id):
        if not self.client.is_ready():
            return
        message = {
            "type": "color_sync_request"
        }
        try:
            self.client.send_message_to(target_steam_id, 2, 1, json.dumps(message).encode('utf-8'))
        except Exception as e:
            print(f"Error requesting color sync from {target_steam_id}: {e}")


    def _sync_colors_with_lobby(self):
        if not self.current_lobby_id or not self.client.is_ready():
            return
        try:
            my_id = self.client.own_steam_id()
            members = self.client.get_lobby_members(self.current_lobby_id)
            for member_steam_id in members:
                if member_steam_id == my_id:
                    continue

                self._send_color_sync(member_steam_id, self.my_drawing_color)

                if member_steam_id not in self.peer_colors:
                    self._request_color_sync(member_steam_id)
                    self.peer_colors[member_steam_id] = "#CCCCCC"
                    self.append_chat(f"[System] Proactively requested color from {member_steam_id}", my_id)

        except Exception as e:
            print(f"Error synchronizing colors with lobby: {e}")

    # --- Canvas Drawing Methods ---
    def start_draw(self, event):
        self.last_x, self.last_y = event.x, event.y

    def draw_line(self, event):
        if self.last_x is not None and self.last_y is not None:
            x, y = event.x, event.y
            self.drawing_canvas.create_line((self.last_x, self.last_y, x, y), width=2, fill=self.my_drawing_color, capstyle=tk.ROUND, smooth=tk.TRUE)
            self.draw.line([self.last_x, self.last_y, x, y], fill=self.my_drawing_color, width=2, joint="curve")

            self.send_drawing_segment(self.last_x, self.last_y, x, y, self.my_drawing_color)

            self.last_x, self.last_y = x, y

    def stop_draw(self, event):
        self.last_x, self.last_y = None, None

    def clear_canvas(self):
        self.drawing_canvas.delete("all")
        self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.send_clear_canvas_command()

    def send_drawing_segment(self, x1, y1, x2, y2, color):
        if not self.current_lobby_id:
            return

        drawing_data = {
            "type": "drawing",
            "payload": {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "color": color
            }
        }
        json_data = json.dumps(drawing_data).encode('utf-8')

        try:
            my_id = self.client.own_steam_id()
            members = self.client.get_lobby_members(self.current_lobby_id)
            for member_steam_id in members:
                if member_steam_id == my_id:
                    continue
                self.client.send_message_to(member_steam_id, 2, 1, json_data)
        except Exception as e:
            print(f"Error sending drawing segment: {e}")

    def display_received_drawing_segment(self, sender_steam_id, payload):
        x1 = payload["x1"]
        y1 = payload["y1"]
        x2 = payload["x2"]
        y2 = payload["y2"]
        color = payload["color"]

        if self.peer_colors.get(sender_steam_id) != color:
            self.peer_colors[sender_steam_id] = color

        self.drawing_canvas.create_line((x1, y1, x2, y2), width=2, fill=color, capstyle=tk.ROUND, smooth=tk.TRUE)
        self.draw.line([x1, y1, x2, y2], fill=color, width=2, joint="curve")

    def send_clear_canvas_command(self):
        if not self.current_lobby_id:
            return
        clear_command = {
            "type": "clear_canvas"
        }
        json_data = json.dumps(clear_command).encode('utf-8')
        try:
            my_id = self.client.own_steam_id()
            members = self.client.get_lobby_members(self.current_lobby_id)
            for member_steam_id in members:
                if member_steam_id == my_id:
                    continue
                self.client.send_message_to(member_steam_id, 2, 1, json_data)
        except Exception as e:
            print(f"Error sending clear canvas command: {e}")

    def clear_canvas_remote(self):
        self.drawing_canvas.delete("all")
        self.image = Image.new("RGB", (self.canvas_width, self.canvas_height), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.append_chat("[System] Canvas cleared by another peer.", self.client.own_steam_id())


if __name__ == "__main__":
    app = SteamApp()
    app.mainloop()