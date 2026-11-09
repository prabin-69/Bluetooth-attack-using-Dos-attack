"""Textual terminal dashboard for local lab state."""

from __future__ import annotations


def create_dashboard(database_path):
    try:
        from textual.app import App, ComposeResult
        from textual.widgets import Footer, Header, Static
    except ImportError as exc:
        raise RuntimeError("Dashboard requires Textual; install project requirements.") from exc
    from blueforce.analytics.metrics import actual_host_metrics
    from blueforce.analytics.metrics import lab_metrics
    from blueforce.database.repository import Repository
    from blueforce.core.state_manager import StateManager

    class Dashboard(App):
        TITLE = "BLUEFORCE X | Analyze. Simulate. Detect. Defend."
        BINDINGS = [("q", "quit", "Quit"), ("r", "refresh", "Refresh")]
        CSS = """
        Screen { background: #07111b; color: #d7e4f0; }
        #panel { border: round #168aad; padding: 1 2; height: auto; }
        """

        def compose(self) -> ComposeResult:
            yield Header()
            yield Static("Loading local BLUEFORCE X state...", id="panel")
            yield Footer()

        def on_mount(self) -> None:
            self._boot_messages = [
                "Initializing isolated laboratory...",
                "Loading detection and analytics modules...",
                "Connecting to local SQLite history...",
                "Safety boundary verified: simulation-only mode.",
            ]
            self._startup_timer = self.set_interval(0.12, self.advance_startup)
            self.set_interval(2, self.refresh_panel)

        def advance_startup(self) -> None:
            panel = self.query_one("#panel", Static)
            if self._boot_messages:
                message = self._boot_messages.pop(0)
                panel.update(f"BLUEFORCE X\n{message}")
            else:
                self._startup_timer.stop()
                self.refresh_panel()

        def action_refresh(self) -> None:
            self.refresh_panel()

        def refresh_panel(self) -> None:
            repository = Repository(database_path)
            try:
                state = StateManager(repository).snapshot()
                host = actual_host_metrics()
                labs = repository.labs()
                content = [
                    " ____  _   _ _____ _____ ___  ____  ____   ____ _____",
                    "| __ )| | | | ____| __  / _ \\|  _ \\|  _ \\ / ___| ____|",
                    "|  _ \\| | | |  _| | |_) | | | | |_) | |_) | |   |  _|",
                    "| |_) | |_| | |___|  _ <| |_| |  _ <|  _ <| |___| |___",
                    "|____/ \\___/|_____|_| \\_\\___/|_| \\_\\_| \\_\\\\____|_____|",
                    "Analyze. Simulate. Detect. Defend.",
                    "SYNTHETIC BLUETOOTH SECURITY LAB",
                    "Safety boundary: simulated activity only; no radio operations.",
                    "",
                    *[f"{key.replace('_', ' ').title()}: {value}"
                      for key, value in state.items()],
                    "",
                    "LATEST LAB METRICS (SIMULATED):",
                    *(["No laboratory created yet."]
                      if not labs else [
                          f"{key.replace('_', ' ').title()}: {value}"
                          for key, value in lab_metrics(repository, labs[-1]["id"]).items()
                      ]),
                    "",
                    f"ACTUAL HOST METRICS (NOT SIMULATED): {host}",
                    "",
                    "Run `blueforce simulation start --help` to launch a virtual scenario.",
                ]
                self.query_one("#panel", Static).update("\n".join(content))
            finally:
                repository.close()

    return Dashboard()


def run_dashboard(database_path) -> int:
    create_dashboard(database_path).run()
    return 0
