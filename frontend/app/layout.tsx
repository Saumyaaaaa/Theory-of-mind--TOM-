import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Learner-State Scaffolding Tutor",
  description: "Socratic tutoring web app with cognitive state scaffolding",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
