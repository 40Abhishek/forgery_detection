import { useNavigate } from "react-router-dom";
import React, { useRef, useState } from "react";
import { uploadFile } from "../services/api";

export default function FileUploader() {
  const inputRef = useRef(null);
  const navigate = useNavigate();

  const [files, setFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ✅ Handle file selection (IMAGE + PDF)
  const handleFiles = (selectedFiles) => {
    const fileArray = Array.from(selectedFiles);

    const validFiles = [];
    let hasInvalid = false;

    fileArray.forEach((file) => {
      if (
        file.type.startsWith("image/") ||
        file.type === "application/pdf"
      ) {
        validFiles.push(file);
      } else {
        hasInvalid = true;
      }
    });

    if (hasInvalid) {
      setError("Only image or PDF files are allowed.");
    } else {
      setError("");
    }

    if (validFiles.length > 0) {
      setFiles((prev) => [...prev, ...validFiles]);
    }
  };

  // Drag & Drop
  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    handleFiles(e.dataTransfer.files);
  };

  // Remove file
  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  // Upload + Navigate
  const handleUpload = async () => {
    if (files.length === 0) return;

    try {
      setLoading(true);

      const res = await uploadFile(files[0]); // single file

      console.log("API RESPONSE:", res);

      setLoading(false);

      // 🔥 Send result to Result page
      navigate("/result", { state: { results: res } });

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
            Upload Image or PDF
          </h2>

          <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-2">
            JPG, PNG, JPEG, PDF supported
          </p>

          <input
            ref={inputRef}
            type="file"
            multiple
            accept="image/*,.pdf"
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

      </div>
    </div>
  );
}