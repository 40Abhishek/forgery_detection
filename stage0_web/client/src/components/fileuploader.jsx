import { useNavigate } from "react-router-dom";
import React, { useRef, useState, useCallback } from "react";
import { uploadFile } from "../api/api";

export default function FileUploader() {
  const inputRef = useRef(null);
  const navigate = useNavigate();

  const [files, setFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);

  // ✅ File validation constants
  const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
  const ALLOWED_TYPES = {
    "image/jpeg": "JPG",
    "image/png": "PNG",
    "image/jpg": "JPG",
    "application/pdf": "PDF",
  };

  // ✅ Get file icon based on type
  const getFileIcon = (type) => {
    if (type.startsWith("image/")) return "🖼️";
    if (type === "application/pdf") return "📄";
    return "📎";
  };

  // ✅ Format file size for display
  const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
  };

  // ✅ Validate files with detailed error messages
  const validateFiles = useCallback((selectedFiles) => {
    const fileArray = Array.from(selectedFiles);
    const validFiles = [];
    const errors = [];

    fileArray.forEach((file) => {
      // Check file type
      if (!ALLOWED_TYPES[file.type]) {
        errors.push(`❌ ${file.name}: File type not supported. Use JPG, PNG, or PDF.`);
        return;
      }

      // Check file size
      if (file.size > MAX_FILE_SIZE) {
        errors.push(
          `❌ ${file.name}: File too large (${formatFileSize(file.size)}). Max: ${formatFileSize(MAX_FILE_SIZE)}`
        );
        return;
      }

      validFiles.push(file);
    });

    return { validFiles, errors };
  }, []);

  // ✅ Handle file selection
  const handleFiles = useCallback((selectedFiles) => {
    const { validFiles, errors } = validateFiles(selectedFiles);

    if (errors.length > 0) {
      setError(errors.join("\n"));
      setSuccess("");
    } else {
      setError("");
      setSuccess("");
    }

    if (validFiles.length > 0) {
      setFiles((prev) => [...prev, ...validFiles]);
    }
  }, [validateFiles]);

  // ✅ Drag & Drop handlers
  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type !== "dragleave" && e.type !== "drop");
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  // ✅ Remove file
  const removeFile = useCallback((index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // ✅ Upload handler with progress
  const handleUpload = useCallback(async () => {
    if (files.length === 0) return;

    try {
      setLoading(true);
      setError("");
      setSuccess("");
      setUploadProgress(0);

      const file = files[0];
      
      // Simulate progress (optional - only if your API supports it)
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) return 90; // Stop at 90% until complete
          return prev + Math.random() * 30;
        });
      }, 300);

      // Upload file
      const res = await uploadFile(file);

      clearInterval(progressInterval);
      setUploadProgress(100);

      // Validate response
      if (!res || !res.result) {
        throw new Error("Invalid response from server");
      }

      console.log("✅ API RESPONSE:", res);

      setSuccess(`✅ Upload successful! Verdict: ${res.result.verdict}`);
      
      // Wait a moment then navigate
      setTimeout(() => {
        navigate("/result", { state: { results: res } });
      }, 500);

    } catch (error) {
      console.error("❌ Upload Error:", error);
      
      // Detailed error messages
      let errorMsg = "Upload failed. ";
      if (error.message.includes("timeout")) {
        errorMsg += "Server took too long to respond. Try a smaller file.";
      } else if (error.message.includes("Network")) {
        errorMsg += "Check your internet connection.";
      } else if (error.response?.status === 413) {
        errorMsg += "File too large.";
      } else if (error.response?.status === 500) {
        errorMsg += "Server error. Try again later.";
      } else {
        errorMsg += error.message || "Try again.";
      }

      setError(errorMsg);
      setUploadProgress(0);

    } finally {
      setLoading(false);
    }
  }, [files, navigate]);

  // ✅ Clear all files
  const handleClearAll = useCallback(() => {
    setFiles([]);
    setError("");
    setSuccess("");
    setUploadProgress(0);
  }, []);

  return (
    <div className="w-full px-4 sm:px-6 lg:px-0 max-w-2xl mx-auto py-8">
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-2xl shadow-sm p-4 sm:p-6 md:p-8">

        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Document Analysis
          </h1>
          <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400">
            Upload images or PDFs to detect tampering and forgery
          </p>
        </div>

        {/* Upload Box */}
        <div
          onClick={() => inputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={handleDrag}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          className={`
            cursor-pointer border-2 border-dashed rounded-xl 
            p-6 sm:p-8 md:p-12 text-center transition-all duration-200
            ${
              dragActive
                ? "border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20 scale-105"
                : "border-gray-300 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800/50"
            }
          `}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
          aria-label="Upload file area"
        >
          <div className="text-4xl sm:text-5xl md:text-6xl mb-3 sm:mb-4 transition-transform duration-200 hover:scale-110">
            {dragActive ? "📥" : "📂"}
          </div>

          <h2 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white mb-2">
            {dragActive ? "Drop files here" : "Upload Image or PDF"}
          </h2>

          <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
            Drag & drop or click to browse
          </p>

          <p className="text-[10px] sm:text-xs text-gray-500 dark:text-gray-500 mt-2">
            JPG, PNG, PDF • Max {formatFileSize(MAX_FILE_SIZE)}
          </p>

          <input
            ref={inputRef}
            type="file"
            multiple={false}
            accept={Object.keys(ALLOWED_TYPES).join(",")}
            className="hidden"
            onChange={(e) => e.target.files && handleFiles(e.target.files)}
            aria-label="File input"
          />
        </div>

        {/* Error Message */}
        {error && (
          <div className="mt-4 p-3 sm:p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-xs sm:text-sm text-red-700 dark:text-red-300 font-medium whitespace-pre-wrap">
              {error}
            </p>
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="mt-4 p-3 sm:p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
            <p className="text-xs sm:text-sm text-green-700 dark:text-green-300 font-medium">
              {success}
            </p>
          </div>
        )}

        {/* File List */}
        {files.length > 0 && (
          <div className="mt-6 sm:mt-8">
            <div className="space-y-3 sm:space-y-4">
              {files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center gap-3 sm:gap-4 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-3 sm:px-4 py-3 sm:py-4 group hover:border-gray-300 dark:hover:border-gray-600 transition-all"
                >
                  {/* File Icon */}
                  <div className="flex-shrink-0 text-2xl">
                    {getFileIcon(file.type)}
                  </div>

                  {/* File Info */}
                  <div className="flex-grow min-w-0">
                    <p className="text-xs sm:text-sm font-medium text-gray-900 dark:text-white truncate">
                      {file.name}
                    </p>
                    <p className="text-[10px] sm:text-xs text-gray-500 dark:text-gray-400">
                      {formatFileSize(file.size)} • {ALLOWED_TYPES[file.type] || "Unknown"}
                    </p>
                  </div>

                  {/* Remove Button */}
                  <button
                    onClick={() => removeFile(index)}
                    disabled={loading}
                    className="flex-shrink-0 p-1 text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    aria-label={`Remove ${file.name}`}
                    title="Remove file"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}

              {/* Upload Progress Bar */}
              {loading && uploadProgress > 0 && (
                <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              )}

              {/* Upload Button */}
              <button
                onClick={handleUpload}
                disabled={loading || files.length === 0}
                className={`
                  w-full py-2.5 sm:py-3 px-4 rounded-lg font-medium text-sm sm:text-base
                  transition-all duration-200
                  ${
                    loading
                      ? "bg-gray-300 dark:bg-gray-700 text-gray-700 dark:text-gray-300 cursor-not-allowed"
                      : "bg-black text-white hover:bg-gray-900 dark:bg-white dark:text-black dark:hover:bg-gray-100 active:scale-95"
                  }
                `}
                aria-busy={loading}
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" fill="none" opacity="0.3" />
                      <path d="M12 2a10 10 0 010 20" stroke="currentColor" strokeWidth="2" />
                    </svg>
                    Processing... {uploadProgress > 0 && `${Math.round(uploadProgress)}%`}
                  </span>
                ) : (
                  "🚀 Upload & Analyze"
                )}
              </button>

              {/* Clear All Button */}
              {files.length > 0 && !loading && (
                <button
                  onClick={handleClearAll}
                  className="w-full py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white text-sm font-medium transition-colors"
                >
                  Clear All
                </button>
              )}
            </div>
          </div>
        )}

        {/* Info Text */}
        {files.length === 0 && !error && (
          <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <p className="text-xs sm:text-sm text-blue-700 dark:text-blue-300">
              💡 Supported formats: <strong>JPG, PNG, PDF</strong> up to <strong>{formatFileSize(MAX_FILE_SIZE)}</strong>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}