import axios from "axios";

const API = "http://localhost:5000/api";

// Upload file
export const uploadFile = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const res = await axios.post(`${API}/upload`, formData, {
    headers: {
      "Content-Type": "multipart/form-data"
    }
  });

  return res.data;
};

// Fetch all past results
export const fetchResults = async () => {
  const res = await axios.get(`${API}/results`);
  return res.data;
};