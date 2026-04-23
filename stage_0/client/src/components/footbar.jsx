import React from "react";

const Footer = () => {
  return (
    <footer className="border-t border-gray-200 dark:border-gray-800 mt-16 transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-6 py-10">
        
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
          
         
          <div className="flex items-center gap-3">
            
            <span className="text-lg font-semibold text-gray-800 dark:text-white">
              QuantumDocs
            </span>
          </div>

          
          <div className="flex gap-8 text-sm font-medium text-gray-500 dark:text-gray-400">
            <a href="#" className="hover:text-black dark:hover:text-white transition">
              Privacy
            </a>
            <a href="#" className="hover:text-black dark:hover:text-white transition">
              Terms
            </a>
            <a href="/contact" className="hover:text-black dark:hover:text-white transition">
              Contact
            </a>
          </div>
        </div>

        
        <div className="mt-8 text-center text-sm text-gray-400 dark:text-gray-500">
          © {new Date().getFullYear()} QuantumDocs. All rights reserved.
        </div>

      </div>
    </footer>
  );
};

export default Footer;
