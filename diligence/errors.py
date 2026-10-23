"""Consistent JSON errors. Internal details are logged, never returned."""

from __future__ import annotations

import logging
from typing import Any

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException

LOGGER = logging.getLogger("diligence")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def error_response(status: int, code: str, message: str, details: Any = None):
    body: dict[str, Any] = {"code": code, "message": message, "request_id": getattr(g, "request_id", None)}
    if details is not None:
        body["details"] = details
    return jsonify({"error": body}), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def _api_error(error: ApiError):
        return error_response(error.status, error.code, error.message, error.details)

    @app.errorhandler(413)
    def _too_large(_error):
        limit = app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024)
        return error_response(413, "payload_too_large", f"The upload exceeds the {limit:g} MB limit.")

    @app.errorhandler(HTTPException)
    def _http_error(error: HTTPException):
        if not request.path.startswith("/api"):
            return error
        return error_response(error.code or 500, (error.name or "error").lower().replace(" ", "_"), error.description or "")

    @app.errorhandler(Exception)
    def _unexpected(error: Exception):
        LOGGER.exception("Unhandled error on %s %s", request.method, request.path)
        return error_response(500, "internal_error", "An unexpected error occurred. Please try again.")
