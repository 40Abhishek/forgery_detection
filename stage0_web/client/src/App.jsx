import { useEffect, useState } from "react";
import "./App.css";

import Navbar from "./components/navbar";
import Footer from "./components/footbar";
import Terms from "./pages/Terms";
import Privacy from "./pages/Privacy";
import Contact from "./pages/Contact";
import Main from "./pages/Main";
import Features from "./pages/Features";
import About from "./pages/About";
import GetStarted from "./pages/GetStarted";
import Result from "./pages/result"

import { Routes, Route } from "react-router-dom";

function App() {
  const [darkMode, setDarkMode] = useState(() => {
  return localStorage.getItem("theme") === "dark";
});

  useEffect(() => {
  if (darkMode) {
    document.documentElement.classList.add("dark");
    localStorage.setItem("theme", "dark");
  } else {
    document.documentElement.classList.remove("dark");
    localStorage.setItem("theme", "light");
  }
}, [darkMode]);

  return (
    <div className="flex flex-col min-h-screen bg-white dark:bg-gray-950 transition-colors duration-300">

      <Navbar darkMode={darkMode} setDarkMode={setDarkMode} />

      <div className="flex-grow">
      <Routes>
        <Route path="/" element={<Main />} />
        <Route path="/features" element={<Features />} />
        <Route path="/about" element={<About />} />
        <Route path="/get-started" element={<GetStarted />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/contact" element={<Contact />} />
        <Route path="/result" element={<Result />} />
      </Routes>
      </div>

      <Footer />
    </div>
  );
}

export default App;