const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");

// ✅ /tmp for result — writable on Render
const RESULT_PATH = "/tmp/result.json";

// ✅ main.py path relative to this file (goes up to repo root)
const MAIN_PY_PATH = path.join(__dirname, "../../../../main.py");

exports.uploadFile = (req, res) => {
  try {
    console.log("CONTROLLER HIT");

    if (!req.file) {
      return res.status(400).json({ success: false, message: "No file uploaded" });
    }

    const filePath = path.resolve(req.file.path);
    console.log("Sending to Python:", filePath);

    // ✅ python3 not python — Render uses Ubuntu
    const python = spawn("python3", [MAIN_PY_PATH, filePath]);

    python.stdout.on("data", (data) => {
      console.log("PY:", data.toString());
    });

    python.stderr.on("data", (data) => {
      console.log("PY ERROR:", data.toString());
    });

    python.on("close", (code) => {
      console.log("Python finished with code:", code);

      setTimeout(() => {
        let result = null;

        try {
          console.log("Reading JSON from:", RESULT_PATH);

          if (fs.existsSync(RESULT_PATH)) {
            const raw = fs.readFileSync(RESULT_PATH, "utf-8");
            result = JSON.parse(raw);
            console.log("RESULT:", result);
          } else {
            console.log("result.json NOT FOUND");
          }
        } catch (err) {
          console.log("JSON ERROR:", err.message);
        }

        return res.status(200).json({
          success: true,
          message: "File processed",
          file: req.file.filename,
          result: result || { message: "No result found" }
        });
      }, 800);
    });

  } catch (err) {
    console.log("Controller Error:", err);
    return res.status(500).json({
      success: false,
      message: err.message
    });
  }
};