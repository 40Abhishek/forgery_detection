console.log("Server file started (DEBUG MODE)");

process.on("uncaughtException", (err) => {
  console.log("Uncaught Exception:", err);
});

process.on("unhandledRejection", (err) => {
  console.log("Unhandled Rejection:", err);
});

const express = require("express");
const cors = require("cors");

const app = express();

app.use(cors({
  origin: [
    "http://localhost:5173",
    "https://docstampdetect.onrender.com/"
  ]
}));

app.use(express.json());

app.get("/", (req, res) => {
  console.log("Home route hit");
  res.send("Server is alive");
});

const uploadRoutes = require("./routes/uploadRoutes");
app.use("/api", uploadRoutes);

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(" Server running on port", PORT);
});