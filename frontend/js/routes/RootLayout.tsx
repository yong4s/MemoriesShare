import React from 'react';
import { Outlet } from 'react-router';

import TopNav from '@/js/components/TopNav';
import { AuthProvider } from '@/js/context/AuthContext';
import { ThemeProvider } from '@/js/context/ThemeContext';
import { ToastProvider } from '@/js/context/ToastContext';

const RootLayout = () => (
  <ThemeProvider>
    <AuthProvider>
      <ToastProvider>
        <div className="bg-mesh-animated min-h-screen">
          <TopNav />
          <Outlet />
        </div>
      </ToastProvider>
    </AuthProvider>
  </ThemeProvider>
);

export default RootLayout;
