import './globals.css';

export const metadata = {
  title: 'Hermes Team Cloud Admin',
  description: 'Hermes Team Cloud administration dashboard'
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
