const multer = require("multer");
const path = require("path");
const fs = require("fs");

const uploadDir = path.join(__dirname, "../../../images");

if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}

const storage = multer.diskStorage({
  destination: function (req, file, cb) {
    console.log("📁 Uploading to:", uploadDir); // debug
    cb(null, uploadDir);
  },

  filename: function (req, file, cb) {
    const ext = path.extname(file.originalname);

    const cleanName = file.originalname
      .replace(/\s+/g, "_")         // remove spaces
      .replace(/[^\w.-]/g, "");     // remove special chars

    cb(null, Date.now() + "-" + cleanName);
  }
});

const upload = multer({ storage });

module.exports = upload;