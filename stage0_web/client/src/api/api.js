import axios from "axios";

const API = axios.create({
  baseURL: "https://dtds-mm7w.onrender.com/api"
});

export const uploadFile = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const res = await API.post("/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });

  return res.data.result;
};