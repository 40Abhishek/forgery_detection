import { useEffect, useState } from "react";
import "./App.css";

import Navbar from "./components/navbar";
import Footer from "./components/footbar";
import Main from "./pages/Main";


function App() {
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [darkMode]);

  return (
    <div className="flex flex-col min-h-screen bg-white dark:bg-gray-950 transition-colors duration-300">

      <Navbar darkMode={darkMode} setDarkMode={setDarkMode} />

      
      <Main/>

      <Footer />
    </div>
  );
}

export default App;
