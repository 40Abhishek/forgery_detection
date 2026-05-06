console.log("🚀 Server file started (PRODUCTION READY)");

process.on("uncaughtException", (err) => {
  console.log("❌ Uncaught Exception:", err);
});

process.on("unhandledRejection", (err) => {
  console.log("❌ Unhandled Rejection:", err);
});

const express = require("express");
const cors = require("cors");
const path = require("path");

const app = express();

app.use(cors());
app.use(express.json());

// ✅ API FIRST
const uploadRoutes = require("./routes/uploadRoutes");
app.use("/api", uploadRoutes);

// ✅ HEALTH
app.get("/health", (req, res) => {
  res.send("OK");
});

// ✅ FRONTEND BUILD
const clientPath = path.join(process.cwd(), "stage0_web/client/dist");
app.use(express.static(clientPath));

// ✅ FINAL FIX (NO ROUTE PATTERN)
app.use((req, res) => {
  res.sendFile(path.join(clientPath, "index.html"));
});

// ✅ PORT
const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`🔥 Server running on port ${PORT}`);
});