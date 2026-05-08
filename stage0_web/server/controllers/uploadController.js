const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");

// ✅ FIXED PATH (NO SPACE FOLDER RECOMMENDED)
const RESULT_PATH = path.join(__dirname, "../../../results/result.json");

exports.uploadFile = (req, res) => {
  try {
    console.log("🔥 CONTROLLER HIT");

    if (!req.file) {
      return res.status(400).json({ success: false, message: "No file uploaded" });
    }

    const filePath = path.resolve(req.file.path);
    console.log("📂 Sending to Python:", filePath);

    const python = spawn("python", [
      path.join(__dirname, "../../../main.py"),
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

      // 🔥 WAIT before reading JSON (VERY IMPORTANT)
      setTimeout(() => {

        let result = null;

        try {
          console.log("📄 Reading JSON from:", RESULT_PATH);

          if (fs.existsSync(RESULT_PATH)) {
            const raw = fs.readFileSync(RESULT_PATH, "utf-8");
            result = JSON.parse(raw);

            console.log("📊 RESULT:", result);
          } else {
            console.log("❌ result.json NOT FOUND");
          }

        } catch (err) {
          console.log("❌ JSON ERROR:", err.message);
        }

        return res.status(200).json({
          success: true,
          message: "File processed",
          file: req.file.filename,
          result: result || { message: "No result found" }
        });

      }, 800); // 🔥 delay fix
    });

  } catch (err) {
    console.log("❌ Controller Error:", err);

    return res.status(500).json({
      success: false,
      message: err.message
    });
  }
};