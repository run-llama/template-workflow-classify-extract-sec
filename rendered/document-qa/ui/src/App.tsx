import { ApiProvider } from "@llamaindex/ui";
import Home from "./pages/Home";
import { Theme } from "@radix-ui/themes";
import { clients } from "@/libs/clients";
import { useEffect } from "react";

export default function App() {
  // Apply dark mode based on system preference
  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    const updateDarkMode = (e: MediaQueryListEvent | MediaQueryList) => {
      if (e.matches) {
        document.documentElement.classList.add("dark");
      } else {
        document.documentElement.classList.remove("dark");
      }
    };

    // Set initial state
    updateDarkMode(mediaQuery);

    // Listen for changes
    mediaQuery.addEventListener("change", updateDarkMode);

    return () => mediaQuery.removeEventListener("change", updateDarkMode);
  }, []);
  return (
    <Theme>
      <ApiProvider clients={clients}>
        <Home />
      </ApiProvider>
    </Theme>
  );
}
