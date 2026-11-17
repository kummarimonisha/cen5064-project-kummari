export const metadata = {
  title: "AI Resume Optimizer & ATS Matcher",
  description: "Upload a resume, score it against a job, and rewrite bullets with AI.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
