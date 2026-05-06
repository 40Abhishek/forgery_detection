const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");

exports.uploadFile = (req, res) => {
  try {
    console.log("🔥 CONTROLLER HIT");

    if (!req.file) {
      return res.status(400).json({
        success: false,
        message: "No file uploaded"
      });
    }

    const filePath = path.resolve(req.file.path);

    // ✅ CREATE UNIQUE RESULT FILE
    const resultFile = path.join(
      __dirname,
      "../../../results",
      `${Date.now()}-result.json`
    );

    console.log("📂 File sent to Python:", filePath);
    console.log("📄 Result will be saved at:", resultFile);

    // ✅ USE python3 (IMPORTANT FOR RENDER)
    const python = spawn("python3", [
      path.join(__dirname, "../../../main.py"),
      filePath,
      resultFile
    ]);

    python.stdout.on("data", (data) => {
      console.log("PY:", data.toString());
    });

    python.stderr.on("data", (data) => {
      console.log("❌ PY ERROR:", data.toString());
    });

    python.on("close", () => {
      console.log("✅ Python finished");

      // 🔥 WAIT for JSON creation
      setTimeout(() => {
        let result = null;

        try {
          console.log("📄 Reading JSON from:", resultFile);

          if (fs.existsSync(resultFile)) {
            const raw = fs.readFileSync(resultFile, "utf-8");
            result = JSON.parse(raw);
            console.log("📊 RESULT:", result);
          } else {
            console.log("❌ Result file not found");
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

      }, 1000); // slight delay for safety
    });

  } catch (err) {
    console.log("❌ Controller Error:", err);

    return res.status(500).json({
      success: false,
      message: err.message
    });
  }
};