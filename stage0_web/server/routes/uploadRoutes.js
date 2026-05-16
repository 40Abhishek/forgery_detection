const express = require("express");
const router = express.Router();
const path = require("path");
const fs = require("fs");
const multer = require("multer");
const { uploadFile } = require("../controllers/uploadController");

// ✅ Use /tmp — only writable directory on Render
const uploadDir = "/tmp/uploads";

if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const cleanName = file.originalname
      .replace(/\s+/g, "_")
      .replace(/[^\w.-]/g, "");
    cb(null, Date.now() + "-" + cleanName);
  }
});

const upload = multer({ storage });

// ✅ Single route only — duplicate removed
router.post("/upload", upload.single("file"), uploadFile);

module.exports = router;