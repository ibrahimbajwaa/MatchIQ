import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ApiError } from "./api/client";
import { Shell } from "./components/Shell";
import { Empty } from "./components/States";
import { FixturesPage } from "./pages/FixturesPage";
import { HomePage } from "./pages/HomePage";
import { LeaderboardsPage } from "./pages/LeaderboardsPage";
import { ModelPage } from "./pages/ModelPage";
import { PlayerPage } from "./pages/PlayerPage";
import { ScoutPage } from "./pages/ScoutPage";
import { TeamsPage } from "./pages/TeamsPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // A 4xx will not fix itself on retry; a dropped connection or a 5xx might.
      retry: (count, error) => !(error instanceof ApiError && error.status >= 400 && error.status < 500) && count < 2,
      refetchOnWindowFocus: false,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Shell />}>
            <Route index element={<HomePage />} />
            <Route path="leaderboards" element={<LeaderboardsPage />} />
            <Route path="players/:id" element={<PlayerPage />} />
            <Route path="scout" element={<ScoutPage />} />
            <Route path="teams" element={<TeamsPage />} />
            <Route path="fixtures" element={<FixturesPage />} />
            <Route path="model" element={<ModelPage />} />
            <Route path="*" element={<div className="wrap"><h1 className="page-title">Page not found</h1><Empty>That page doesn't exist. Use the menu to find your way back.</Empty></div>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
