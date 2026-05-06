const express = require("express");
const router = express.Router();
const multer = require("multer");
const path = require("path");
const fs = require("fs");

const { uploadFile } = require("../controllers/uploadController");

const uploadDir = path.join(__dirname, "../../../images");

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

// ✅ ONLY HERE
router.post("/upload", upload.single("file"), uploadFile);

router.post("/upload", (req, res, next) => {
  console.log("🔥 ROUTE HIT");
  next();
}, upload.single("file"), uploadFile);

module.exports = router;