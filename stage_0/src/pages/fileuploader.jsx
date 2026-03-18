import React, { useRef, useState } from "react";

export default function FileUploader() {
  const inputRef = useRef(null);
  const [files, setFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);

  const handleFiles = (selectedFiles) => {
    const fileArray = Array.from(selectedFiles);
    setFiles((prev) => [...prev, ...fileArray]);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    handleFiles(e.dataTransfer.files);
  };

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  return (
    <div className="w-full max-w-2xl">

      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm p-8 transition-colors duration-300">

        {/* Upload Box */}
        <div
          onClick={() => inputRef.current.click()}
          onDrop={handleDrop}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          className={`cursor-pointer border-2 border-dashed rounded-xl p-12 text-center transition-all duration-300
          ${
            dragActive
              ? "border-black dark:border-white bg-gray-100 dark:bg-gray-800"
              : "border-gray-300 dark:border-gray-700 hover:border-black dark:hover:border-white"
          }`}
        >
          <div className="text-5xl mb-4">📂</div>

          <h2 className="text-lg font-semibold text-gray-800 dark:text-white">
            Upload PDF or Images
          </h2>

          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            Drag & drop files here or click to browse
          </p>

          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".pdf,image/*"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="mt-8 space-y-4">
            {files.map((file, index) => (
              <div
                key={index}
                className="flex justify-between items-center bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-3 transition-colors"
              >
                <div className="truncate">
                  <p className="text-sm font-medium text-gray-800 dark:text-white truncate">
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>

                <button
                  onClick={() => removeFile(index)}
                  className="text-gray-400 hover:text-red-500 transition font-bold"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}
