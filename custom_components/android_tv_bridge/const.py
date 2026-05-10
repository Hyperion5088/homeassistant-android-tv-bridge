"""Constants for Android TV Bridge."""

from __future__ import annotations

DOMAIN = "android_tv_bridge"

CONF_ADB_KEY_PATH = "adb_key_path"
CONF_ADB_PORT = "adb_port"
CONF_DEVICE_CLASS = "device_class"
CONF_ENABLE_REMOTE_PROTOCOL = "enable_remote_protocol"
CONF_HOST = "host"
CONF_HIDDEN_APPS = "hidden_apps"
CONF_HIDDEN_SOURCES = "hidden_sources"
CONF_NAME = "name"
CONF_POLL_INTERVAL = "poll_interval"
CONF_PROFILE = "profile"
CONF_REMOTE_CERT_PATH = "remote_cert_path"
CONF_REMOTE_KEY_PATH = "remote_key_path"
CONF_SOURCE_FILTER = "source_filter"
CONF_SOURCE_MAP = "source_map"

DEFAULT_ADB_PORT = 5555
DEFAULT_REMOTE_PORT = 6466
DEFAULT_POLL_INTERVAL = 10
MIN_POLL_INTERVAL = 2

DEVICE_CLASS_ANDROID_TV = "androidtv"
DEVICE_CLASS_FIRE_TV = "firetv"

PROFILE_GENERIC = "generic"
PROFILE_TCL_GOOGLE_TV = "tcl_google_tv"
PROFILE_FIRE_TV = "fire_tv"

PLATFORMS = ["media_player", "remote", "select", "sensor"]
