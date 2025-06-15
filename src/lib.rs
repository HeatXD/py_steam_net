mod net_client;

use pyo3::prelude::*;

use crate::net_client::PySteamClient;

#[pymodule]
fn py_steam_net(py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PySteamClient>()?;

    let global = Py::new(py, PySteamClient::new())?;
    m.add("py_steam_net", global)?;

    Ok(())
}