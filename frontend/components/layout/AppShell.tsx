"use client";

import React, { useState, useEffect, useCallback } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import styles from "./AppShell.module.css";

export interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const pathname = usePathname();
  const [prevPathname, setPrevPathname] = useState(pathname);

  // Close drawer during render if pathname changes (React recommended pattern)
  if (prevPathname !== pathname) {
    setPrevPathname(pathname);
    setIsMobileNavOpen(false);
  }

  const handleCloseNav = useCallback(() => {
    setIsMobileNavOpen(false);
  }, []);

  const handleToggleNav = useCallback(() => {
    setIsMobileNavOpen((prev) => !prev);
  }, []);

  // Handle Escape key to close mobile nav
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && isMobileNavOpen) {
        handleCloseNav();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isMobileNavOpen, handleCloseNav]);

  return (
    <div className={styles.shell}>
      {/* Mobile Backdrop */}
      {isMobileNavOpen && (
        <div
          className={styles.backdrop}
          onClick={handleCloseNav}
          aria-hidden="true"
        />
      )}

      {/* Primary Sidebar Navigation */}
      <Sidebar
        isOpen={isMobileNavOpen}
        onClose={handleCloseNav}
        currentPath={pathname || "/"}
      />

      {/* Main Page Area */}
      <div className={styles.mainWrapper}>
        <Header
          onToggleNav={handleToggleNav}
          isNavOpen={isMobileNavOpen}
          currentPath={pathname || "/"}
        />

        <main id="main-content" tabIndex={-1} className={styles.content}>
          {children}
        </main>
      </div>
    </div>
  );
}
