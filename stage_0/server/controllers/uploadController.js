const axios = require("axios");
const fs = require("fs");
const path = require("path");

exports.uploadFile = async (req, res) => {
  try {
    const filePath = path.resolve(req.file.path);

    console.log("📂 Uploaded:", filePath);

  
    const response = await axios.post("http://127.0.0.1:8000/detect", {
      filePath: filePath
    });

    const { result, confidence } = response.data;

    res.json({
      filename: req.file.originalname,
      result,
      confidence
    });

    setTimeout(() => {
      if (fs.existsSync(filePath)) {
        fs.unlink(filePath, (err) => {
          if (err) console.error("❌ Delete failed:", err);
          else console.log("✅ File deleted:", filePath);
        });
      }
    }, 1000);

  } catch (error) {
    console.error("❌ Error:", error.message);

    res.status(500).json({
      message: "Processing failed. Is Python server running?"
    });
  }
};