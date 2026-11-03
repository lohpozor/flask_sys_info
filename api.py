from flask import Blueprint
from metrics import get_info, get_metrics
from version import APP_VERSION

api = Blueprint("api", __name__, url_prefix="/api")


@api.route("/info")         # итоговый адрес: /api/info
def info():
    return {**get_info(), "version": APP_VERSION}


@api.route("/metrics")      # итоговый адрес: /api/metrics
def metrics():
    return get_metrics()
