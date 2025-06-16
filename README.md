# py_steam_net

Python bindings for Steamworks networking lobbies and messages. This library enables interaction with Steam lobbies and messaging from Python applications, utilizing Rust via [pyo3](https://pyo3.rs/) and the [steamworks-rs](https://docs.rs/steamworks/latest/steamworks/) crate, and built with [Maturin](https://www.maturin.rs/).

---

## 🌟 Features

* **Steam Client Management**: Initialize and deinitialize the Steam client.

* **Lobby Functionality**:

    * Create various lobby types (Private, Friends Only, Public, Invisible).

    * Join existing lobbies by ID.

    * Leave active lobbies.

    * Retrieve lobby member lists.

* **Messaging System**:

    * Send messages to Steam users within a connected lobby.

    * Receive incoming messages via a callback mechanism.

* **Real-time Callbacks**:

    * **Lobby Changes**: Notifications for lobby state updates (e.g., member joins/leaves).

    * **Message Reception**: Callback for incoming messages, providing sender's Steam ID and content.

    * **Connection Failures**: Callback for network connection issues.

---

## 🛠️ Installation

### Prerequisites

* **Rust Toolchain**: Install Rust using `rustup`.

* **Python 3.8+**: Compatible Python version required.

* **Steamworks SDK**: `steam_api64.dll` (or equivalent for OS) required in application's executable directory or Python path for the example application.

### Installation

`py_steam_net` is not yet available on PyPI. However, pre-built wheels for various platforms are available in the [GitHub Releases](https://github.com/your-username/py_steam_net/releases) section of the repository. You can download the appropriate wheel file for your system and install it using pip:

```bash
pip install py_steam_net-x.y.z-cpXX-cpXX-your_platform.whl
````

### Building from Source

Requires `maturin`:

```bash
# Clone the repository
git clone [https://github.com/your-username/py_steam_net.git](https://github.com/your-username/py_steam_net.git) # Replace with actual repo URL
cd py_steam_net

# Install maturin
pip install maturin

# Build and install in development mode
maturin develop --release
```

This compiles the Rust code and installs the Python package.

-----

## 🚀 Usage

`PySteamClient` exposes core functionality. A simplified example for client initialization and lobby creation:

```python
import py_steam_net
import ctypes
import os
import sys

# IMPORTANT: Ensure steam_api64.dll (or equivalent for your OS) is accessible.
# For bundled applications (e.g., with PyInstaller), you might need to
# include it with the application.
def load_steam_api_dll():
    if hasattr(sys, '_MEIPASS'):
        dll_path = os.path.join(sys._MEIPASS, "steam_api64.dll")
    else:
        dll_path = os.path.join(os.path.dirname(__file__), "steam_api64.dll")
    try:
        ctypes.WinDLL(dll_path) # Just load it, no need to assign to a variable if not used directly
    except OSError as e:
        print(f"Error loading steam_api64.dll: {e}. Ensure it's in the correct directory.")
        sys.exit(1)

load_steam_api_dll()

def on_lobby_created(lobby_id, error=None):
    if error:
        print(f"Failed to create lobby: {error}")
    else:
        print(f"Lobby created with ID: {lobby_id}")

# Create a Steam client instance
client = py_steam_net.PySteamClient()

# Initialize the client with your App ID (e.g., 480 for Spacewar)
try:
    client.init(480)
    print(f"Steam client initialized: {client.is_ready()}")

    # Create a public lobby with a max of 4 members
    client.create_lobby(2, 4, on_lobby_created)

    # In a real application, you would run callbacks and receive messages in a loop
    # import time
    # for _ in range(100): # Run callbacks for a short period to allow lobby creation to complete
    #     client.run_callbacks()
    #     time.sleep(0.016)

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    # Always deinitialize the client when done
    if client.is_ready():
        client.deinit()
        print("Steam client deinitialized.")
```

For a comprehensive example, refer to `example/test.py`.

### Callback Signatures

  * `set_lobby_changed_callback(callback_fn)`:

      * `callback_fn(lobby_id: int, user_changed: int, making_change: int, member_state_change: int)`

  * `set_message_recv_callback(callback_fn)`:

      * `callback_fn(sender_steam_id: int, msg_bytes: bytes)`

  * `set_connection_failed_callback(callback_fn)`:

      * `callback_fn(steam_id: int, reason: str)`

### Available Methods

  * `PySteamClient()`: Constructor.

  * `init(app_id: int)`: Initializes client.

  * `deinit()`: Deinitializes client.

  * `is_ready() -> bool`: Returns `True` if client is initialized.

  * `run_callbacks()`: Runs pending Steam API callbacks.

  * `receive_messages(channel: int, max_messages: int)`: Receives messages on a channel.

  * `create_lobby(lobby_type: int, max_members: int, callback_fn: Callable[[int, str | None], None])`: Creates a lobby. `lobby_type`: `0` (Private), `1` (FriendsOnly), `2` (Public), `3` (Invisible).

  * `join_lobby(lobby_id: int, callback_fn: Callable[[int, str | None], None])`: Joins a lobby.

  * `leave_lobby(lobby_id: int)`: Leaves a lobby.

  * `get_lobby_members(lobby_id: int) -> list[int]`: Returns Steam IDs of lobby members.

  * `send_message_to(steam_id: int, message_type: int, channel: int, message: bytes)`: Sends byte message to a Steam ID. `message_type` corresponds to `steamworks::networking_types::SendFlags` (e.g., `2` for `RELIABLE`).

  * `own_steam_id() -> int`: Returns current user's Steam ID.

-----

## 🤝 Contributing

Contributions are welcome. Open an issue or pull request on the GitHub repository.

-----

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](https://www.google.com/search?q=LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Jamie Meyer

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
