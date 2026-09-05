# -*- coding: utf-8 -*-
"""Volatility2 legacy analysis service - see README.md for why this exists
and how it's isolated from the rest of the stack.

Python 2.7 (volatility2's hard requirement). Bottle for the HTTP surface -
zero dependencies beyond itself, which matters more than usual on a runtime
that no longer receives security patches: fewer packages, smaller surface.
"""
from __future__ import print_function

import json

from bottle import Bottle, HTTPError, request, response, run  # noqa: E402

from catalog import PLUGIN_CATALOG, PLUGIN_NAMES  # noqa: E402
from vol2_runner import Vol2Error, identify, run_plugin  # noqa: E402

app = Bottle()


def _json(handler):
    def wrapped(*args, **kwargs):
        response.content_type = "application/json"
        return json.dumps(handler(*args, **kwargs))
    return wrapped


@app.route("/health")
@_json
def health():
    return {"status": "ok"}


@app.route("/plugins")
@_json
def plugins():
    return {"plugins": PLUGIN_CATALOG}


@app.post("/identify")
@_json
def do_identify():
    body = request.json or {}
    image_path = body.get("image_path")
    if not image_path:
        raise HTTPError(400, json.dumps({"detail": "image_path is required"}))
    try:
        return identify(image_path)
    except Vol2Error as exc:
        raise HTTPError(502, json.dumps({"detail": str(exc)}))


@app.post("/run")
@_json
def do_run():
    body = request.json or {}
    image_path = body.get("image_path")
    profile = body.get("profile")
    plugin_name = body.get("plugin_name")
    extra_args = body.get("extra_args") or []

    if not image_path or not profile or not plugin_name:
        raise HTTPError(400, json.dumps({"detail": "image_path, profile, and plugin_name are required"}))
    if plugin_name not in PLUGIN_NAMES:
        raise HTTPError(404, json.dumps({"detail": "Unknown legacy plugin: {0}".format(plugin_name)}))
    if not isinstance(extra_args, list) or not all(isinstance(a, (str, unicode)) for a in extra_args):  # noqa: F821
        raise HTTPError(400, json.dumps({"detail": "extra_args must be a list of strings"}))

    try:
        return run_plugin(image_path, profile, plugin_name, extra_args)
    except Vol2Error as exc:
        raise HTTPError(502, json.dumps({"detail": str(exc)}))


if __name__ == "__main__":
    run(app, host="0.0.0.0", port=8200)
