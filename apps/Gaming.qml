import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import org.kde.plasma.plasma5support as PlasmaSupport

ApplicationWindow {
    id: hub
    visible: true
    width: 800
    height: 610
    minimumWidth: 620
    minimumHeight: 460
    title: "Nova Gaming Hub"

    property var games: []
    property var game: null
    property string message: ""
    property bool busy: false
    NovaStyle { id: tokens }
    palette.highlight: tokens.accent

    function invoke(action, payload) {
        if (busy)
            return
        busy = true
        message = ""
        const encoded = encodeURIComponent(JSON.stringify(payload)).replace(/[!'()*~]/g,
            char => "%" + char.charCodeAt(0).toString(16))
        runner.connectSource("/usr/bin/nova-gaming ui " + action + " " + encoded)
    }

    function editGame(game) {
        addGame.gameId = game ? game.id : ""
        gameName.text = game ? game.name : ""
        executable.text = game ? game.path : ""
        kind.currentIndex = game && game.kind === "wine" ? 1 : 0
        runtime.text = game ? game.runtime || "" : ""
        artwork.text = game && game.art ? decodeURIComponent(game.art.replace(/^file:\/\//, "")) : ""
        launchArgs.text = game ? JSON.stringify(game.args || []) : ""
        addGame.open()
    }

    Component.onCompleted: invoke("library", null)

    PlasmaSupport.DataSource {
        id: runner
        engine: "executable"
        interval: 0
        onNewData: (source, data) => {
            if (data["exit code"] === undefined)
                return
            disconnectSource(source)
            hub.busy = false
            if (Number(data["exit code"]) !== 0) {
                hub.message = String(data["stderr"] || "").trim() || "Gaming action failed."
                return
            }
            const response = JSON.parse(String(data["stdout"]))
            if (!Array.isArray(response))
                return
            if (/ ui (library|save|add|remove) /.test(source)) {
                const identifier = hub.game ? hub.game.id : ""
                hub.games = response
                hub.game = hub.games.find(item => item.id === identifier) || null
            } else {
                hub.message = response.filter(line => line).join("\n")
            }
        }
    }

    header: ToolBar {
        RowLayout {
            anchors.fill: parent
            anchors.margins: tokens.compact
            Button { text: "Refresh"; enabled: !hub.busy; onClicked: hub.invoke("library", null) }
            Button { text: "Add game"; onClicked: hub.editGame(null) }
            Button { text: "Gaming setup"; onClicked: setup.open() }
            Button { text: "Controller"; onClicked: hub.invoke("shortcut", "controller") }
            Button { text: "Capture"; onClicked: capture.open() }
            Item { Layout.fillWidth: true }
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: tokens.gutter
        spacing: tokens.gutter

        ListView {
            id: library
            Layout.preferredWidth: 280
            Layout.fillHeight: true
            clip: true
            model: hub.games
            ScrollBar.vertical: ScrollBar {}
            delegate: NovaCard {
                required property var modelData
                width: library.width
                highlighted: hub.game && hub.game.id === modelData.id
                text: (modelData.favorite ? "★ " : "") + modelData.name
                onClicked: hub.game = modelData
            }
            Label {
                anchors.centerIn: parent
                width: parent.width - 20
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                text: "No installed games found"
                visible: !hub.games.length && !hub.busy
            }
        }

        ScrollView {
            id: details
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            ColumnLayout {
                width: details.availableWidth
                spacing: 8
                NovaNotice { text: hub.message }
                NovaLoading { visible: hub.busy }
                Label {
                    Layout.fillWidth: true
                    text: hub.game ? hub.game.name : "Select a game"
                    textFormat: Text.PlainText
                    font.bold: true
                    wrapMode: Text.Wrap
                }
                Image {
                    visible: hub.game && hub.game.art !== ""
                    source: hub.game ? hub.game.art : ""
                    asynchronous: true
                    fillMode: Image.PreserveAspectFit
                    sourceSize.width: 320
                    Layout.fillWidth: true
                    Layout.preferredHeight: visible ? 120 : 0
                }
                Label {
                    visible: !!hub.game
                    text: {
                        if (!hub.game)
                            return ""
                        let minutes = hub.game.kind === "steam" ? hub.game.minutes :
                            (hub.game.seconds === undefined ? null : Math.floor(hub.game.seconds / 60))
                        const recent = hub.game.last ? new Date(hub.game.last * 1000).toLocaleDateString() : "Unavailable"
                        return "Last played: " + recent + "   •   Playtime: " +
                            (minutes === null || minutes === undefined ? "Unavailable" : minutes + " min")
                    }
                }
                RowLayout {
                    visible: !!hub.game
                    Button { text: "Play"; enabled: !hub.busy; onClicked: hub.invoke("launch", hub.game.id) }
                    Button { text: "Storage"; enabled: !hub.busy; onClicked: hub.invoke("storage", hub.game.id) }
                    Button { text: "Open folder"; enabled: !hub.busy; onClicked: hub.invoke("folder", hub.game.id) }
                    Button {
                        text: "ProtonDB"
                        visible: hub.game && hub.game.kind === "steam"
                        onClicked: Qt.openUrlExternally(hub.game.protondb)
                    }
                }
                RowLayout {
                    visible: hub.game && hub.game.kind !== "steam"
                    Button { text: "Edit launch"; onClicked: hub.editGame(hub.game) }
                    Button { text: "Remove from library"; onClicked: hub.invoke("remove", hub.game.id) }
                }
                CheckBox { id: favorite; visible: !!hub.game; text: "Favorite" }
                ComboBox {
                    id: profile
                    visible: !!hub.game
                    model: ["gaming", "balanced", "turbo", "eco", "ultra-lite"]
                    Accessible.name: "Per-game performance profile"
                }
                CheckBox { id: overlay; visible: !!hub.game; text: "MangoHud overlay" }
                TextField {
                    id: hotkey
                    visible: !!hub.game && overlay.checked
                    placeholderText: "Super_L+g"
                    Accessible.name: "MangoHud shortcut"
                }
                CheckBox { id: effects; visible: !!hub.game; text: "Reduce desktop effects during play" }
                CheckBox { id: gamescope; visible: !!hub.game; text: "Use Gamescope" }
                Button {
                    visible: !!hub.game
                    enabled: !hub.busy
                    text: "Save game settings"
                    onClicked: hub.invoke("save", { id: hub.game.id, favorite: favorite.checked,
                        profile: profile.currentText, overlay: overlay.checked, effects: effects.checked,
                        gamescope: gamescope.checked,
                        hotkey: hotkey.text || "Super_L+g" })
                }
                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    visible: hub.game && hub.game.kind === "steam"
                    text: hub.game && hub.game.client === "flatpak"
                        ? "Use Steam’s Properties → Compatibility for Proton versions. For this sandbox, configure MangoHud and launch options inside Steam."
                        : "Choose Proton in Steam’s Properties → Compatibility. To enable saved Nova settings, paste the command below into Steam’s Launch Options."
                }
                TextField {
                    Layout.fillWidth: true
                    readOnly: true
                    selectByMouse: true
                    visible: hub.game && hub.game.kind === "steam" && hub.game.client === "native"
                    text: visible ? "/usr/bin/nova-gaming steam " + hub.game.id.split(":")[1] + " %command%" : ""
                }
                Label {
                    Layout.fillWidth: true
                    wrapMode: Text.Wrap
                    text: "Proton is Steam’s Wine-based compatibility layer. Wine and Bottles run Windows applications separately. Some anti-cheat titles and Roblox are unsupported on Linux."
                }
            }
        }
    }

    onGameChanged: {
        favorite.checked = game ? !!game.favorite : false
        profile.currentIndex = game ? Math.max(0, profile.find(game.profile || "gaming")) : 0
        overlay.checked = game ? !!game.overlay : false
        effects.checked = game ? !!game.effects : false
        gamescope.checked = game ? !!game.gamescope : false
        hotkey.text = game ? (game.hotkey || "Super_L+g") : ""
    }

    Dialog {
        id: addGame
        property string gameId: ""
        title: "Add an installed game or legitimate installer"
        anchors.centerIn: parent
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: hub.invoke("add", { id: gameId, name: gameName.text, path: executable.text,
            kind: kind.currentIndex === 0 ? "native" : "wine", runtime: runtime.text,
            art: artwork.text, args: launchArgs.text })
        ColumnLayout {
            TextField { id: gameName; Layout.fillWidth: true; placeholderText: "Game name" }
            TextField { id: executable; Layout.fillWidth: true; placeholderText: "/absolute/path/to/game-or-installer" }
            ComboBox { id: kind; model: ["Native executable", "Windows (Wine)"] }
            TextField { id: runtime; visible: kind.currentIndex === 1; placeholderText: "Wine executable (default: wine)" }
            TextField { id: artwork; Layout.fillWidth: true; placeholderText: "Artwork path (optional)" }
            TextField { id: launchArgs; Layout.fillWidth: true; placeholderText: 'Arguments as JSON, e.g. ["--windowed"]' }
        }
    }

    Dialog {
        id: setup
        title: "Optional gaming tools"
        anchors.centerIn: parent
        standardButtons: Dialog.Close
        ColumnLayout {
            ComboBox {
                id: tool
                textRole: "name"
                valueRole: "key"
                model: [
                    { name: "Steam + Proton", key: "steam" },
                    { name: "Steam (native Debian, if configured)", key: "native-steam" },
                    { name: "Wine", key: "wine" },
                    { name: "Bottles", key: "bottles" },
                    { name: "Lutris", key: "lutris" },
                    { name: "Heroic (Epic and GOG)", key: "heroic" },
                    { name: "GameMode", key: "gamemode" },
                    { name: "MangoHud", key: "overlay" },
                    { name: "MangoHud (Flatpak extension)", key: "flatpak-overlay" },
                    { name: "Gamescope (native, if configured)", key: "gamescope" },
                    { name: "Gamescope (Flatpak extension)", key: "flatpak-gamescope" },
                    { name: "Vulkan diagnostics", key: "vulkan" },
                    { name: "NVIDIA driver detection", key: "nvidia-detect" },
                    { name: "Install detected NVIDIA driver", key: "nvidia-driver" },
                    { name: "Minecraft Java (Prism Launcher)", key: "minecraft" },
                    { name: "RetroArch", key: "emulation" },
                    { name: "Godot", key: "development" },
                    { name: "OBS Studio", key: "recording" }
                ]
            }
            Button {
                text: "Review installation"
                onClicked: { hub.invoke("setup", tool.currentValue); setup.close() }
            }
            Button {
                text: "Check graphics hardware"
                onClicked: { hub.invoke("graphics", null); setup.close() }
            }
        }
    }

    Dialog {
        id: capture
        title: "Game capture"
        anchors.centerIn: parent
        standardButtons: Dialog.Close
        ColumnLayout {
            Button {
                text: "Spectacle"
                onClicked: { hub.invoke("shortcut", "spectacle"); capture.close() }
            }
            Button {
                text: "Open OBS (if installed)"
                onClicked: { hub.invoke("shortcut", "obs"); capture.close() }
            }
        }
    }
}
