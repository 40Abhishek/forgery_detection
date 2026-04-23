import React, { useState } from "react";
import { Menu, X, Sun, Moon } from "lucide-react";


const Navbar = ({ darkMode, setDarkMode }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="bg-white/80 dark:bg-gray-950/80 backdrop-blur-md border-b border-gray-200 dark:border-gray-800 sticky top-0 z-50 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-6 py-3 flex justify-between items-center">

        
        <div className="flex items-center">
          <img
            src="/quantum.png"
            alt="QuantumDocs Logo"
            className="h-12 w-auto object-contain"
          />
        </div>

       
        <div className="hidden md:flex items-center space-x-8 font-medium text-gray-600 dark:text-gray-300">
          <a href="/" className="hover:text-black dark:hover:text-white transition">
            Home
          </a>
          <a href="/features" className="hover:text-black dark:hover:text-white transition">
            Features
          </a>
          <a href="/about" className="hover:text-black dark:hover:text-white transition">
            About
          </a>

          
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="p-2 rounded-lg border border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
          >
            {darkMode ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          <button className="bg-black dark:bg-white text-white dark:text-black px-5 py-2 rounded-lg hover:opacity-90 transition">
            Get Started
          </button>
        </div>

        
        <div className="md:hidden flex items-center gap-3">

          
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="p-2 rounded-lg border border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
          >
            {darkMode ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="text-gray-700 dark:text-gray-300"
          >
            {isOpen ? <X size={26} /> : <Menu size={26} />}
          </button>
        </div>
      </div>

      
      {isOpen && (
        <div className="md:hidden bg-white dark:bg-gray-950 border-t border-gray-200 dark:border-gray-800 px-6 py-4 space-y-4 font-medium text-gray-600 dark:text-gray-300 transition-colors duration-300">
          <a
            href="/"
            className="block hover:text-black dark:hover:text-white transition"
            onClick={() => setIsOpen(false)}
          >
            Home
          </a>
          <a
            href="#"
            className="block hover:text-black dark:hover:text-white transition"
            onClick={() => setIsOpen(false)}
          >
            Features
          </a>
          <a
            href="#"
            className="block hover:text-black dark:hover:text-white transition"
            onClick={() => setIsOpen(false)}
          >
            About
          </a>

          <button className="w-full bg-black dark:bg-white text-white dark:text-black py-2 rounded-lg hover:opacity-90 transition">
            Get Started
          </button>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
