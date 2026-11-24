import QtQuick
import org.kde.plasma.plasma5support as PlasmaSupport

Item {
    id: bridge
    visible: false
    required property string executable
    property string pending: ""
    readonly property bool busy: pending !== ""
    signal completed(string action, var result)
    signal failed(string action, string message)

    function invoke(action, payload) {
        if (busy)
            return
        pending = action
        const encoded = encodeURIComponent(JSON.stringify(payload)).replace(/[!'()*~]/g,
            char => "%" + char.charCodeAt(0).toString(16))
        engine.connectSource(executable + " " + action + " " + encoded)
    }

    PlasmaSupport.DataSource {
        id: engine
        engine: "executable"
        interval: 0
        onNewData: (source, data) => {
            if (data["exit code"] === undefined)
                return
            disconnectSource(source)
            const action = bridge.pending
            bridge.pending = ""
            if (Number(data["exit code"]) !== 0) {
                bridge.failed(action, String(data["stderr"] || "").trim() || "The operation failed.")
                return
            }
            try {
                bridge.completed(action, JSON.parse(String(data["stdout"])))
            } catch (error) {
                bridge.failed(action, "The operation returned an invalid response.")
            }
        }
    }
}
