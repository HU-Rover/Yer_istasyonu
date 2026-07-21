from flask import Flask, jsonify
from onvif import ONVIFCamera
import os
try:
    from flask_cors import CORS
    HAS_CORS = True
except ImportError:
    HAS_CORS = False

app = Flask(__name__)
if HAS_CORS:
    CORS(app)

@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    return response


CAMERAS = {}


def build_camera_config(prefix):

    if prefix == "CAMERA1":
        return {
            "ip": "192.168.88.100",
            "port": 2020,
            "username": "tepegoz31",
            "password": "tepegoz31",
        }

    elif prefix == "CAMERA2":
        return {
            "ip": "192.168.88.101",
            "port": 2020,
            "username": "tepegoz32",
            "password": "tepegoz32",
        }

    else:
        raise ValueError(f"Bilinmeyen kamera prefix: {prefix}")


def init_camera(camera_id, prefix):
    config = build_camera_config(prefix)
    state = {
        "ready": False,
        "error": "",
        "cam": None,
        "media": None,
        "ptz": None,
        "profile": None,
        "move": None,
        "stop": None,
        "config": config,
    }

    if not config["ip"]:
        state["error"] = f"{camera_id}: IP adresi ayarlanmamış"
        return state

    try:
        state["cam"] = ONVIFCamera(config["ip"], config["port"], config["username"], config["password"])
        state["media"] = state["cam"].create_media_service()
        state["ptz"] = state["cam"].create_ptz_service()
        state["profile"] = state["media"].GetProfiles()[0]

        state["move"] = state["ptz"].create_type("ContinuousMove")
        state["move"].ProfileToken = state["profile"].token

        state["stop"] = state["ptz"].create_type("Stop")
        state["stop"].ProfileToken = state["profile"].token

        state["ready"] = True
    except Exception as exc:
        state["error"] = str(exc)

    return state


for camera_id, prefix in [("tapo_kamera_1", "CAMERA1"), ("tapo_kamera_2", "CAMERA2")]:
    CAMERAS[camera_id] = init_camera(camera_id, prefix)


@app.route("/health", methods=["GET"])
def health_all():
    return jsonify({camera_id: {"ready": state["ready"], "error": state["error"]} for camera_id, state in CAMERAS.items()})


@app.route("/health/<camera_id>", methods=["GET"])
def health_camera(camera_id):
    if camera_id not in CAMERAS:
        return jsonify({"status": "error", "message": "Bilinmeyen kamera"}), 404

    state = CAMERAS[camera_id]
    if state["ready"]:
        return jsonify({"status": "ok", "camera": camera_id, "ip": state["config"]["ip"]})
    return jsonify({"status": "error", "camera": camera_id, "message": state["error"]}), 500


@app.route("/<camera_id>/move/<direction>", methods=["GET", "POST"])
def move_camera(camera_id, direction):
    if camera_id not in CAMERAS:
        return jsonify({"status": "error", "message": "Bilinmeyen kamera"}), 404

    state = CAMERAS[camera_id]
    if not state["ready"]:
        return jsonify({"status": "error", "camera": camera_id, "message": state["error"]}), 500

    direction = direction.lower()
    mapping = {
        "up": (0.0, 0.5),
        "down": (0.0, -0.5),
        "left": (-0.5, 0.0),
        "right": (0.5, 0.0),
    }

    if direction not in mapping:
        return jsonify({"status": "error", "message": "Geçersiz yön"}), 400

    x, y = mapping[direction]
    state["move"].Velocity = {"PanTilt": {"x": x, "y": y}}
    state["ptz"].ContinuousMove(state["move"])

    return jsonify({"status": "ok", "camera": camera_id, "direction": direction})


@app.route("/<camera_id>/stop", methods=["GET", "POST"])
def stop_camera(camera_id):
    if camera_id not in CAMERAS:
        return jsonify({"status": "error", "message": "Bilinmeyen kamera"}), 404

    state = CAMERAS[camera_id]
    if not state["ready"]:
        return jsonify({"status": "error", "camera": camera_id, "message": state["error"]}), 500

    state["ptz"].Stop(state["stop"])
    return jsonify({"status": "ok", "camera": camera_id, "message": "Durdu"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
