import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import AnalysisResult from "./pages/AnalysisResult";
import Home from "./pages/Home";
import Login from "./pages/Login";
import NewAnalysis from "./pages/NewAnalysis";
import Register from "./pages/Register";
import ResumeReview from "./pages/ResumeReview";
import Resumes from "./pages/Resumes";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/" element={<Home />} />
        <Route path="/resumes" element={<Resumes />} />
        <Route path="/resumes/:id" element={<ResumeReview />} />
        <Route path="/analyze" element={<NewAnalysis />} />
        <Route path="/analysis/:id" element={<AnalysisResult />} />
      </Route>
      <Route path="*" element={<div className="p-10 text-center text-slate-500">Page not found.</div>} />
    </Routes>
  );
}
