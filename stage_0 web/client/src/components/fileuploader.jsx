import React, { useRef, useState } from "react";
import { uploadFile } from "../services/api";

export default function FileUploader() {
  const inputRef = useRef(null);
  const [files, setFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [error, setError] = useState("");

  const handleFiles = (selectedFiles) => {
    const fileArray = Array.from(selectedFiles);

    const validFiles = [];
    let hasInvalid = false;

    fileArray.forEach((file) => {
      if (file.type.startsWith("image/")) {
        validFiles.push(file);
      } else {
        hasInvalid = true;
      }
    });

    if (hasInvalid) {
      setError("Only image files are allowed. Please re-upload.");
    } else {
      setError("");
    }

    if (validFiles.length > 0) {
      setFiles((prev) => [...prev, ...validFiles]);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    handleFiles(e.dataTransfer.files);
  };

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setError("Please select at least one image.");
      return;
    }

    try {
      setLoading(true);
      setError("");

      const uploadedResults = [];

      for (let file of files) {
        const res = await uploadFile(file);
        uploadedResults.push(res);
      }

      setResults(uploadedResults);
      setLoading(false);
    } catch (error) {
      console.error(error);
      setError("Upload failed. Try again.");
      setLoading(false);
    }
  };

  return (
    <div className="w-full px-4 sm:px-6 lg:px-0 max-w-2xl mx-auto">

      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm p-4 sm:p-6 md:p-8">

        {/* Upload Box */}
        <div
          onClick={() => inputRef.current.click()}
          onDrop={handleDrop}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          className={`cursor-pointer border-2 border-dashed rounded-xl 
          p-6 sm:p-8 md:p-12 text-center transition-all
          ${
            dragActive
              ? "border-black dark:border-white bg-gray-100 dark:bg-gray-800"
              : "border-gray-300 dark:border-gray-700 hover:border-black dark:hover:border-white"
          }`}
        >
          <div className="text-3xl sm:text-4xl md:text-5xl mb-3 sm:mb-4">📂</div>

          <h2 className="text-base sm:text-lg font-semibold text-gray-800 dark:text-white">
            Upload Only Images
          </h2>

          <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-2">
            JPG, PNG, JPEG supported
          </p>

          <input
            ref={inputRef}
            type="file"
            multiple
            accept="image/*"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>

        {/* Error */}
        {error && (
          <div className="mt-4 text-red-500 text-xs sm:text-sm font-medium">
            {error}
          </div>
        )}

        {/* File List */}
        {files.length > 0 && (
          <div className="mt-6 sm:mt-8 space-y-3 sm:space-y-4">
            {files.map((file, index) => (
              <div
                key={index}
                className="flex flex-col sm:flex-row sm:justify-between sm:items-center 
                gap-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 
                dark:border-gray-700 rounded-lg px-3 sm:px-4 py-3"
              >
                <div className="truncate">
                  <p className="text-xs sm:text-sm font-medium text-gray-800 dark:text-white truncate">
                    {file.name}
                  </p>
                  <p className="text-[10px] sm:text-xs text-gray-500 dark:text-gray-400">
                    {(file.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>

                <button
                  onClick={() => removeFile(index)}
                  className="self-end sm:self-auto text-gray-400 hover:text-red-500 font-bold"
                >
                  ✕
                </button>
              </div>
            ))}

            {/* Upload Button */}
            <button
              onClick={handleUpload}
              className="w-full bg-black text-white py-2.5 sm:py-3 rounded-lg hover:opacity-90 text-sm sm:text-base"
            >
              {loading ? "Processing..." : "Upload & Detect"}
            </button>
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <div className="mt-6 sm:mt-8 space-y-3 sm:space-y-4">
            <h3 className="text-base sm:text-lg font-semibold text-gray-800 dark:text-white">
              Results
            </h3>

            {results.map((res, index) => (
              <div
                key={index}
                className="p-3 sm:p-4 border rounded-lg bg-gray-50 dark:bg-gray-800 text-xs sm:text-sm"
              >
                <p><strong>File:</strong> {res.filename}</p>
                <p><strong>Status:</strong> {res.result}</p>
                <p><strong>Confidence:</strong> {res.confidence}%</p>
              </div>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}