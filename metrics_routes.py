import time
from flask import Blueprint, request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

metrics_bp = Blueprint("metrics", __name__)

REQUEST_COUNT = Counter(
    "flask_forum_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "flask_forum_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"]
)

IN_PROGRESS = Gauge(
    "flask_forum_http_requests_in_progress",
    "HTTP requests currently in progress",
    ["method", "endpoint"]
)


@metrics_bp.before_app_request
def start_timer():
    request._start_time = time.time()

    endpoint = request.endpoint or "unknown"
    method = request.method

    IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()


@metrics_bp.after_app_request
def record_metrics(response):
    endpoint = request.endpoint or "unknown"
    method = request.method
    status = str(response.status_code)

    duration = time.time() - getattr(request, "_start_time", time.time())

    REQUEST_COUNT.labels(
        method=method,
        endpoint=endpoint,
        status=status
    ).inc()

    REQUEST_LATENCY.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)

    IN_PROGRESS.labels(
        method=method,
        endpoint=endpoint
    ).dec()

    return response


@metrics_bp.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)