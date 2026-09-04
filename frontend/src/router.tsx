import { createBrowserRouter } from "react-router-dom";
import { AppLayout } from "./components/AppLayout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Cameras } from "./pages/Cameras";
import { Dashboard } from "./pages/Dashboard";
import { Events } from "./pages/Events";
import { Login } from "./pages/Login";
import { Settings } from "./pages/Settings";
import { Statistics } from "./pages/Statistics";

export const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: "/", element: <Dashboard /> },
          { path: "/cameras", element: <Cameras /> },
          { path: "/events", element: <Events /> },
          { path: "/statistics", element: <Statistics /> },
          { path: "/settings", element: <Settings /> },
        ],
      },
    ],
  },
  { path: "*", element: <Login /> },
]);
