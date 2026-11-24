import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.plasma.plasma5support as PlasmaSupport

ApplicationWindow {
    id: window
    visible: true
    width: 660
    height: 620
    minimumWidth: 450
    minimumHeight: 400
    title: "Nova Performance Center"

    property var sample: null
    property var previous: null
    property bool sampling: false
    property string boot: ""
    property string error: ""
    property var cpuHistory: []
    NovaStyle { id: tokens }
    palette.highlight: tokens.accent

    function requestSample() {
        if (!sampling) {
            sampling = true
            actions.connectSource("/usr/lib/novaos/nova-metrics.py")
        }
    }

    function cpu() {
        if (!previous || !sample)
            return -1
        const total = sample.cpu[0] - previous.cpu[0]
        const idle = sample.cpu[1] - previous.cpu[1]
        return total > 0 ? Math.max(0, Math.min(100, 100 * (total - idle) / total)) : -1
    }

    function intervalDisk() {
        if (!previous || !sample || sample.disk < previous.disk || sample.timestamp <= previous.timestamp)
            return "—"
        return ((sample.disk - previous.disk) / (sample.timestamp - previous.timestamp) / 1048576).toFixed(2) + " MiB/s"
    }

    function memoryText(pair) {
        return pair.map(value => (value / 1024).toFixed(0)).join(" / ") + " MiB"
    }

    Component.onCompleted: actions.connectSource("/usr/lib/novaos/nova-metrics.py boot")

    Timer {
        interval: 2000
        repeat: true
        running: window.visible && window.visibility !== Window.Minimized
        triggeredOnStart: true
        onTriggered: window.requestSample()
    }

    PlasmaSupport.DataSource {
        id: actions
        engine: "executable"
        interval: 0
        onNewData: (source, data) => {
            if (data["exit code"] === undefined)
                return
            disconnectSource(source)
            if (source.endsWith("nova-metrics.py")) {
                window.sampling = false
                if (Number(data["exit code"]) !== 0) {
                    window.error = "Metrics are unavailable."
                    return
                }
                window.previous = window.sample
                window.sample = JSON.parse(String(data["stdout"]))
                if (window.cpu() >= 0) {
                    window.cpuHistory = window.cpuHistory.slice(-29).concat(window.cpu())
                    historyPlot.requestPaint()
                }
                window.error = ""
            } else if (source.endsWith(" boot")) {
                window.boot = String(data["stdout"] || "").trim()
            } else if (source.includes("nova-profile set") && Number(data["exit code"]) !== 0) {
                window.error = String(data["stderr"] || "").trim() || "Could not apply the profile."
            }
        }
    }

    ScrollView {
        anchors.fill: parent
        anchors.margins: tokens.comfortable
        contentWidth: availableWidth

        ColumnLayout {
            width: parent.width
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                Label { text: "Profile"; font.bold: true }
                ComboBox {
                    id: profiles
                    textRole: "name"
                    valueRole: "key"
                    model: [
                        { name: "Balanced", key: "balanced" },
                        { name: "Nova Turbo", key: "turbo" },
                        { name: "Nova Gaming", key: "gaming" },
                        { name: "Nova Eco", key: "eco" },
                        { name: "Nova Ultra Lite", key: "ultra-lite" }
                    ]
                    Component.onCompleted: currentIndex = 0
                    Connections {
                        target: window
                        function onSampleChanged() {
                            const index = profiles.indexOfValue(window.sample.profile)
                            if (index >= 0)
                                profiles.currentIndex = index
                        }
                    }
                    onActivated: actions.connectSource("/usr/bin/nova-profile set " + currentValue)
                }
                Button {
                    text: "Startup Applications"
                    onClicked: actions.connectSource("/usr/bin/systemsettings kcm_autostart")
                }
            }
            Label { text: window.cpu() < 0 ? "CPU —" : "CPU " + window.cpu().toFixed(1) + "%" }
            Canvas {
                id: historyPlot
                Layout.fillWidth: true
                Layout.preferredHeight: 42
                Accessible.name: "CPU utilization history"
                onWidthChanged: requestPaint()
                onPaint: {
                    const context = getContext("2d")
                    context.clearRect(0, 0, width, height)
                    context.strokeStyle = tokens.accent
                    context.lineWidth = 2
                    context.beginPath()
                    window.cpuHistory.forEach((value, index) => {
                        const x = (30 - window.cpuHistory.length + index) * (width - 2) / 29 + 1
                        const y = 1 + (height - 2) * (1 - value / 100)
                        if (index === 0)
                            context.moveTo(x, y)
                        else
                            context.lineTo(x, y)
                    })
                    context.stroke()
                }
            }
            Label { text: "RAM   " + (window.sample ? window.memoryText(window.sample.ram) : "—") }
            Label { text: "Swap   " + (window.sample ? window.memoryText(window.sample.swap) : "—") }
            Label { text: "GPU   " + (window.sample && window.sample.gpu !== null ? window.sample.gpu + "%" : "Unavailable") }
            Label { text: "Highest temperature   " + (window.sample && window.sample.temperature !== null ? window.sample.temperature.toFixed(1) + " °C" : "Unavailable") }
            Label { text: "Storage read + write   " + window.intervalDisk() }
            Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                text: window.boot || "Boot duration unavailable"
            }
            Label { text: "Running processes by resident memory"; font.bold: true }
            Label {
                Layout.fillWidth: true
                text: window.sample ? window.sample.processes.join("\n") : ""
                textFormat: Text.PlainText
                font.family: "Noto Mono"
            }
            NovaNotice { text: window.error }
        }
    }
}
