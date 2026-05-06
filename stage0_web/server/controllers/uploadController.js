const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");

const RESULT_PATH = path.join(__dirname, "../../results/result.json");

exports.uploadFile = (req, res) => {
  try {
    console.log("🔥 CONTROLLER HIT");

    if (!req.file) {
      return res.status(400).json({ success: false, message: "No file uploaded" });
    }

    const filePath = path.resolve(req.file.path);

    console.log("📂 Sending to Python:", filePath);

    // 🔥 RUN PYTHON MAIN.PY
    const python = spawn("python", [
      path.join(__dirname, "../../main.py"),
      filePath
    ]);

    python.stdout.on("data", (data) => {
      console.log("PY:", data.toString());
    });

    python.stderr.on("data", (data) => {
      console.log("PY ERROR:", data.toString());
    });

    python.on("close", () => {

      console.log("✅ Python finished");

      // 🔥 READ RESULT JSON
      let result = null;

      try {
        if (fs.existsSync(RESULT_PATH)) {
          result = JSON.parse(fs.readFileSync(RESULT_PATH, "utf-8"));
        }
      } catch (err) {
        console.log("❌ JSON read error:", err.message);
      }

      // 🔥 SEND RESPONSE TO FRONTEND
      return res.status(200).json({
        success: true,
        message: "File processed",
        file: req.file.filename,
        result: result || { message: "No result found" }
      });
    });

  } catch (err) {
    console.log("❌ Controller Error:", err);

    return res.status(500).json({
      success: false,
      message: err.message
    });
  }
};