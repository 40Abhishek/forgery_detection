import React from "react";
import FileUploader from "../components/fileuploader";

export default function GetStarted() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-16">

      <h1 className="text-4xl font-bold text-center mb-6">
        Get Started
      </h1>

      <p className="text-center text-gray-600 mb-10">
        Upload your document or image and let our system detect forgery instantly.
      </p>

      <div className="flex justify-center">
        <FileUploader />
      </div>

    </div>
  );
}