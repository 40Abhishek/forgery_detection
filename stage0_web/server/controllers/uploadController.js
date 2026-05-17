const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");

const RESULT_PATH = "/tmp/result.json";
const MAIN_PY_PATH = path.join(__dirname, "../../../main.py");

exports.uploadFile = (req, res) => {
  try {
    console.log("CONTROLLER HIT");

    if (!req.file) {
      return res.status(400).json({ success: false, message: "No file uploaded" });
    }

    const filePath = path.resolve(req.file.path);
    const fileName = req.file.filename;
    console.log("Sending to Python:", filePath);

    // ✅ DEBUG: Check if python script exists
    if (!fs.existsSync(MAIN_PY_PATH)) {
      console.log("❌ ERROR: main.py not found at:", MAIN_PY_PATH);
      return res.status(500).json({
        success: false,
        message: "Python script not found",
        path: MAIN_PY_PATH
      });
    }
    console.log("✅ main.py found at:", MAIN_PY_PATH);

    if (fs.existsSync(RESULT_PATH)) {
      fs.unlinkSync(RESULT_PATH);
    }

    // ✅ UNBUFFER PYTHON OUTPUT + increase maxBuffer
    const python = spawn("python3", [
      MAIN_PY_PATH,
      filePath,
      RESULT_PATH
    ], {
      maxBuffer: 10 * 1024 * 1024,  // 10MB buffer
      env: {
        ...process.env,
        PYTHONUNBUFFERED: "1"  // ✅ Force Python to flush output immediately
      }
    });

    console.log("✅ Python process spawned, PID:", python.pid);

    let pythonOutput = "";
    let pythonError = "";
    let pythonStarted = false;

    python.stdout.on("data", (data) => {
      pythonStarted = true;
      pythonOutput += data.toString();
      console.log("PY OUTPUT:", data.toString());
    });

    python.stderr.on("data", (data) => {
      pythonStarted = true;
      pythonError += data.toString();
      console.log("PY ERROR:", data.toString());
    });

    // ✅ Add timeout: Kill Python if it runs > 2 minutes
    const pythonTimeout = setTimeout(() => {
      console.log("⚠️  Python timeout (2 minutes) - killing process");
      python.kill("SIGTERM");
    }, 120000); // 2 minutes

    python.on("close", (code) => {
      clearTimeout(pythonTimeout);
      console.log("✅ Python finished with code:", code);
      
      if (!pythonStarted) {
        console.log("⚠️  WARNING: Python didn't output anything!");
      }

      // ✅ DELETE UPLOADED FILE
      try {
        if (fs.existsSync(filePath)) {
          fs.unlinkSync(filePath);
          console.log(`🗑️  Deleted uploaded file: ${fileName}`);
        }
      } catch (err) {
        console.log(`⚠️  Failed to delete uploaded file: ${err.message}`);
      }

      if (code !== 0) {
        console.log("❌ Python execution failed with code:", code);
        return res.status(500).json({
          success: false,
          message: "Python processing failed",
          error: pythonError || "No error output",
          pythonOutput: pythonOutput
        });
      }

      // ✅ WAIT UP TO 10 SECONDS FOR RESULT
      let attempts = 0;
      const maxAttempts = 100; // 100 attempts × 100ms = 10 seconds
      const checkInterval = setInterval(() => {
        attempts++;
        
        if (attempts % 10 === 0) {  // Log every 10 attempts (every 1 second)
          console.log(`Checking for result.json (attempt ${attempts}/${maxAttempts})...`);
        }

        if (fs.existsSync(RESULT_PATH)) {
          clearInterval(checkInterval);

          try {
            console.log("✅ Reading JSON from:", RESULT_PATH);
            const raw = fs.readFileSync(RESULT_PATH, "utf-8");
            const result = JSON.parse(raw);
            console.log("✅ RESULT PARSED:", result.verdict, result.risk_score);

            try {
              fs.unlinkSync(RESULT_PATH);
              console.log("🗑️  Deleted result.json");
            } catch (err) {
              console.log(`⚠️  Failed to delete result.json: ${err.message}`);
            }

            cleanupOldUploads();

            return res.status(200).json({
              success: true,
              message: "File processed successfully",
              file: fileName,
              result: result
            });
          } catch (err) {
            console.log("❌ JSON PARSE ERROR:", err.message);
            
            try {
              fs.unlinkSync(RESULT_PATH);
            } catch (e) {
              // ignore
            }
            
            return res.status(500).json({
              success: false,
              message: "Error parsing results",
              error: err.message
            });
          }
        }

        if (attempts >= maxAttempts) {
          clearInterval(checkInterval);
          console.log("❌ result.json NOT FOUND after 10 seconds");
          console.log("Python Output:", pythonOutput);
          console.log("Python Error:", pythonError);
          
          try {
            fs.unlinkSync(RESULT_PATH);
          } catch (e) {
            // ignore
          }
          
          return res.status(500).json({
            success: false,
            message: "Processing timeout — result file not created after 10 seconds",
            pythonOutput: pythonOutput,
            pythonError: pythonError
          });
        }
      }, 100);

    });

    python.on("error", (err) => {
      console.log("❌ Python spawn error:", err);
      
      try {
        if (fs.existsSync(filePath)) {
          fs.unlinkSync(filePath);
          console.log(`🗑️  Deleted uploaded file after error: ${fileName}`);
        }
      } catch (e) {
        // ignore
      }
      
      return res.status(500).json({
        success: false,
        message: "Failed to start Python process",
        error: err.message
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

function cleanupOldUploads() {
  const uploadDir = "/tmp/uploads";
  const oneHourAgo = Date.now() - (60 * 60 * 1000);

  try {
    if (!fs.existsSync(uploadDir)) return;

    const files = fs.readdirSync(uploadDir);
    files.forEach((file) => {
      const filePath = path.join(uploadDir, file);
      const stats = fs.statSync(filePath);

      if (stats.mtimeMs < oneHourAgo) {
        fs.unlinkSync(filePath);
        console.log(`🗑️  Cleaned up old file: ${file}`);
      }
    });
  } catch (err) {
    console.log(`⚠️  Cleanup error: ${err.message}`);
  }
}