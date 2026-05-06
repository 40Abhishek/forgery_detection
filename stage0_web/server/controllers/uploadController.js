const { exec } = require("child_process");
const fs = require("fs");
const path = require("path");

exports.uploadFile = (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ message: "No file uploaded" });
    }

    const filePath = path.resolve(req.file.path);

    console.log("📂 Uploaded:", filePath);

    // 🧠 Run Python
    const command = `python ../stage_1/main.py "${filePath}"`;

    exec(command, (error, stdout, stderr) => {
      if (error) {
        console.error(error);
        return res.status(500).json({ message: "Python failed" });
      }

      let data;
      try {
        data = JSON.parse(stdout);
      } catch (e) {
        return res.status(500).json({ message: "Invalid Python output" });
      }

      res.json({
        filename: req.file.originalname,
        result: data.verdict,
        confidence: data.score
      });

      // 🧹 delete file
      setTimeout(() => {
        if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
      }, 1000);
    });

  } catch (err) {
    console.error(err);
    res.status(500).json({ message: "Server error" });
  }
};