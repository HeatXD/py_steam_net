use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
};

use pyo3::{
    exceptions::PyRuntimeError,
    prelude::*,
    types::{PyBytes, PyList},
};
use steamworks::{
    networking_messages::SessionRequest,
    networking_types::{NetworkingIdentity, SendFlags},
    Client, ClientManager, LobbyChatUpdate, LobbyId, LobbyType, SingleClient, SteamId,
};

#[pyclass(unsendable)]
pub struct PySteamClient {
    client: Option<(Client, SingleClient)>,
    cb_conn_request: Arc<Mutex<Option<Py<PyAny>>>>,
    cb_conn_failed: Arc<Mutex<Option<Py<PyAny>>>>,
    cb_lobby_changed: Arc<Mutex<Option<Py<PyAny>>>>,
    cb_message_recv: Arc<Mutex<Option<Py<PyAny>>>>,
    //store pending session requests
    pending_requests: Arc<Mutex<HashMap<u64, SessionRequest<ClientManager>>>>,
}

#[pymethods]
impl PySteamClient {
    #[new]
    pub fn new() -> Self {
        PySteamClient {
            client: None,
            cb_conn_request: Arc::new(Mutex::new(None)),
            cb_conn_failed: Arc::new(Mutex::new(None)),
            cb_lobby_changed: Arc::new(Mutex::new(None)),
            cb_message_recv: Arc::new(Mutex::new(None)),
            pending_requests: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub fn init(&mut self, app_id: u32) -> PyResult<()> {
        match Client::init_app(app_id) {
            Ok((client, single)) => {
                let cb_lobby_changed_shared = self.cb_lobby_changed.clone();
                client.register_callback::<LobbyChatUpdate, _>(move |update| {
                    Python::with_gil(|py| {
                        if let Some(cb) = &*cb_lobby_changed_shared.lock().unwrap() {
                            let _ = cb.call1(
                                py,
                                (
                                    update.lobby.raw(),
                                    update.user_changed.raw(),
                                    update.making_change.raw(),
                                    update.member_state_change as u64,
                                ),
                            );
                        }
                    });
                });

                let pending_requests_clone = self.pending_requests.clone();
                let cb_connection_req_shared = self.cb_conn_request.clone();
                client
                    .networking_messages()
                    .session_request_callback(move |req| {
                        let steam_id_raw = req.remote().steam_id().unwrap().raw();

                        // Store the session request in the hashmap
                        pending_requests_clone
                            .lock()
                            .unwrap()
                            .insert(steam_id_raw, req);

                        Python::with_gil(|py| {
                            if let Some(cb) = &*cb_connection_req_shared.lock().unwrap() {
                                let _ = cb.call1(py, (steam_id_raw,));
                            }
                        });
                    });

                let cb_connection_failed_shared = self.cb_conn_failed.clone();
                client
                    .networking_messages()
                    .session_failed_callback(move |info| {
                        Python::with_gil(|py| {
                            if let Some(cb) = &*cb_connection_failed_shared.lock().unwrap() {
                                let _ = cb.call1(
                                    py,
                                    (info.identity_remote().unwrap().steam_id().unwrap().raw(),),
                                );
                            }
                        });
                    });

                self.client = Some((client, single));
                Ok(())
            }
            Err(e) => Err(PyRuntimeError::new_err(e.to_string())),
        }
    }

    pub fn deinit(&mut self) {
        self.client = None;
    }

    pub fn is_ready(&self) -> bool {
        self.client.is_some()
    }

    pub fn run_callbacks(&self) {
        if let Some(client) = &self.client {
            client.1.run_callbacks();
        }
    }

    pub fn receive_messages(&self, channel: u32, max_messages: usize) {
        if let Some(client) = &self.client {
            for message in client
                .0
                .networking_messages()
                .receive_messages_on_channel(channel, max_messages)
            {
                Python::with_gil(|py| {
                    if let Some(cb) = &*self.cb_message_recv.lock().unwrap() {
                        // Extract sender steam id and message data
                        let steam_id = message.identity_peer().steam_id().unwrap().raw();
                        let data = message.data();

                        // Call Python callback: cb(steam_id: int, data: bytes)
                        let _ = cb.call1(py, (steam_id, PyBytes::new(py, data)));
                    }
                });
            }
        }
    }

    pub fn create_lobby(&mut self, lobby_type: u32, max_members: u32, cb_on_created: Py<PyAny>) {
        if let Some((client, _)) = &self.client {
            let matchmaking = client.matchmaking();

            let lobby_kind = match lobby_type {
                0 => LobbyType::Private,
                1 => LobbyType::FriendsOnly,
                2 => LobbyType::Public,
                3 => LobbyType::Invisible,
                _ => LobbyType::Private,
            };

            matchmaking.create_lobby(lobby_kind, max_members, move |result| {
                Python::with_gil(|py| match result {
                    Ok(lobby_id) => {
                        let _ = cb_on_created.call1(py, (lobby_id.raw(),));
                    }
                    Err(err) => {
                        let _ = cb_on_created.call1(py, (py.None(), err.to_string()));
                    }
                });
            });
        }
    }

    pub fn join_lobby(&mut self, lobby_id: u64, cb_on_joined: Py<PyAny>) {
        if let Some((client, _)) = &self.client {
            let matchmaking = client.matchmaking();
            matchmaking.join_lobby(LobbyId::from_raw(lobby_id), move |result| {
                Python::with_gil(|py| match result {
                    Ok(lobby_id) => {
                        let _ = cb_on_joined.call1(py, (lobby_id.raw(), py.None()));
                    }
                    Err(e) => {
                        let _ = cb_on_joined.call1(
                            py,
                            (
                                py.None(),
                                PyRuntimeError::new_err(format!("No Lobby Found: {:?}", e)),
                            ),
                        );
                    }
                });
            });
        }
    }

    pub fn leave_lobby(&mut self, lobby_id: u64) {
        if let Some((client, _)) = &self.client {
            let matchmaking = client.matchmaking();
            matchmaking.leave_lobby(LobbyId::from_raw(lobby_id));
        }
    }

    pub fn get_lobby_members(&self, py: Python<'_>, lobby_id: u64) -> PyResult<PyObject> {
        if let Some(client) = &self.client {
            let matchmaking = client.0.matchmaking();
            let lobby = LobbyId::from_raw(lobby_id);
            let members = matchmaking.lobby_members(lobby);

            if members.is_empty() {
                return Err(PyRuntimeError::new_err("Lobby not found or no members"));
            }

            let member_ids: Vec<u64> = members.iter().map(|id| id.raw()).collect();

            let py_list = PyList::new(py, member_ids.clone())?;
            Ok(py_list.into_pyobject(py)?.into())
        } else {
            Err(PyRuntimeError::new_err("Client not initialized"))
        }
    }

    pub fn set_lobby_changed_callback(&mut self, cb: Py<PyAny>) {
        let mut guard = self.cb_lobby_changed.lock().unwrap();
        *guard = Some(cb);
    }

    pub fn set_connection_request_callback(&mut self, cb: Py<PyAny>) {
        let mut guard = self.cb_conn_request.lock().unwrap();
        *guard = Some(cb);
    }

    pub fn set_connection_failed_callback(&mut self, cb: Py<PyAny>) {
        let mut guard = self.cb_conn_failed.lock().unwrap();
        *guard = Some(cb);
    }

    pub fn set_message_recv_callback(&mut self, cb: Py<PyAny>) {
        let mut guard = self.cb_message_recv.lock().unwrap();
        *guard = Some(cb);
    }

    pub fn send_message_to(
        &mut self,
        steam_id: u64,
        message_type: i32,
        channel: u32,
        message: &[u8],
    ) {
        if let Some((client, _)) = &self.client {
            let networking = client.networking_messages();

            let flags = SendFlags::from_bits(message_type).unwrap_or(SendFlags::UNRELIABLE);

            let _ = networking.send_message_to_user(
                NetworkingIdentity::new_steam_id(SteamId::from_raw(steam_id)),
                flags,
                message,
                channel,
            );
        }
    }

    pub fn accept_connection(&mut self, steam_id: u64) {
        let mut pending = self.pending_requests.lock().unwrap();
        if let Some(req) = pending.remove(&steam_id) {
            req.accept();
        }
    }

    pub fn reject_connection(&mut self, steam_id: u64) {
        let mut pending = self.pending_requests.lock().unwrap();
        if let Some(req) = pending.remove(&steam_id) {
            req.reject();
        }
    }
}
