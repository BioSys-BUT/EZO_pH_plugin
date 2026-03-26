# -*- coding: utf-8 -*-
import json
import sqlite3
import click
import busio
from time import sleep
from pioreactor.whoami import get_unit_name, get_assigned_experiment_name
from pioreactor.config import config
from pioreactor.background_jobs.base import BackgroundJobContrib
from pioreactor.utils import clamp
from pioreactor.utils import timing
from pioreactor.utils.timing import RepeatedTimer
from pioreactor import hardware
from pioreactor.background_jobs.leader.mqtt_to_db_streaming import produce_metadata
from pioreactor.background_jobs.leader.mqtt_to_db_streaming import register_source_to_sink
from pioreactor.background_jobs.leader.mqtt_to_db_streaming import TopicToParserToTable
from pioreactor import types as pt
from atlas_ezo_ph import AtlasEzoPH


def __dir__():
    return ['click_pH_reading']


def _ensure_ph_readings_table():
    """Create pH_readings table if it doesn't exist. Runs when plugin loads."""
    try:
        db_path = config.get("storage", "database")
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pH_readings (
                    experiment       TEXT NOT NULL,
                    pioreactor_unit  TEXT NOT NULL,
                    timestamp        TEXT NOT NULL,
                    pH_reading       REAL NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ph_readings_experiment_ix ON pH_readings (experiment)"
            )
    except Exception:
        pass  # Silently ignore on workers or if DB not accessible


_ensure_ph_readings_table()


def parser(topic, payload) -> dict:
    metadata = produce_metadata(topic)
    return {
        "experiment": metadata.experiment,
        "pioreactor_unit": metadata.pioreactor_unit,
        "timestamp": timing.current_utc_timestamp(),
        "pH_reading": float(payload),
    }


register_source_to_sink(
    TopicToParserToTable(
        ["pioreactor/+/+/ph_reading/pH"],
        parser,
        "pH_readings",
    )
)



class PHReader(BackgroundJobContrib):

    job_name="ph_reading"
    published_settings = {
        "pH": {"datatype": "float", "settable": False},
    }

    def __init__(self, unit, experiment, **kwargs) -> None:
        super().__init__(unit=unit, experiment=experiment, plugin_name="ph_reading", **kwargs)

        time_between_readings = config.getfloat("ph_reading.config", "time_between_readings")
        if time_between_readings < 2.0:
            # Surface a clear error to the UI / logs instead of a silent assertion failure.
            self.logger.error(
                "Invalid time_between_readings=%.2f. Minimum allowed is 2.0 seconds.",
                time_between_readings,
            )
            raise ValueError(
                "time_between_readings must be at least 2.0 seconds. "
                "Please increase it in the configuration or Advanced settings."
            )

        # Probe configuration is sourced from `[ph_reading.config]`.
        self.probe = AtlasEzoPH.from_config()
        self.timer_thread = RepeatedTimer(time_between_readings, self.read_pH, job_name=self.job_name, run_immediately=True).start()

    def read_pH(self):
        self.pH = float(self.probe.read_ph(samples=2))
        return self.pH

    def on_ready_to_sleeping(self) -> None:
        self.timer_thread.pause()

    def on_sleeping_to_ready(self) -> None:
        self.timer_thread.unpause()

    def on_disconnect(self) -> None:
        self.timer_thread.cancel()

    # Low-level EZO I2C protocol is implemented in `AtlasEzoPH`.


__plugin_name__ = "ph_reading"
__plugin_version__ = "0.1.0"


@click.command(name="ph_reading")
def click_pH_reading():
    """
    Start continuous pH reading job.
    """
    unit = get_unit_name()

    job = PHReader(
        unit=unit,
        experiment=get_assigned_experiment_name(unit),
    )

    job.block_until_disconnected()

