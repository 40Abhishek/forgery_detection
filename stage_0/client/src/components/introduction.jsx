import React from "react";

const Introduction = () => {
  return (
    <div className="text-center px-4 sm:px-6 lg:px-8 py-8 sm:py-10 md:py-12 lg:py-16 transition-colors duration-300">
      
      <h1 className="
        text-2xl 
        sm:text-3xl 
        md:text-4xl 
        lg:text-5xl 
        font-bold 
        text-gray-800 dark:text-white 
        mb-3 sm:mb-4
        leading-tight
      ">
        Document Forgery Detection
      </h1>

      <p className="
        text-sm 
        sm:text-base 
        md:text-lg 
        text-gray-600 dark:text-gray-300 
        max-w-xs 
        sm:max-w-lg 
        md:max-w-2xl 
        mx-auto
        leading-relaxed
      ">
        Upload images or PDFs and detect tampering in seconds. Multiple
        verification layers ensure high accuracy. Try it now and experience
        the future of document security!
      </p>

    </div>
  );
};

export default Introduction;