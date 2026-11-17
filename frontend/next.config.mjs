/** @type {import('next').NextConfig} */
const nextConfig = {
  // The backend base URL. Change this if the FastAPI server runs elsewhere.
  env: {
    NEXT_PUBLIC_API_BASE: "http://127.0.0.1:8000",
  },
};

export default nextConfig;
