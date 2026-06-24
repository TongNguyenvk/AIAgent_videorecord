import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import axios from "axios";
import {
  Video,
  LogOut,
  User,
  Plus,
  RefreshCw,
  Clock,
  CheckCircle,
  XCircle,
  Loader,
} from "lucide-react";

const UserDashboard = () => {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showSubmitForm, setShowSubmitForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({
    task: "",
    url: "",
    narration: "",
  });

  useEffect(() => {
    fetchJobs();
  }, []);

  const fetchJobs = async () => {
    try {
      const response = await axios.get("/api/jobs/");
      setJobs(response.data.jobs || []);
    } catch (error) {
      console.error("Failed to fetch jobs:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      const payload = {
        task: formData.task,
        url: formData.url,
        narration: formData.narration || undefined,
      };

      await axios.post("/api/queue/submit", payload);

      setFormData({ task: "", url: "", narration: "" });
      setShowSubmitForm(false);
      fetchJobs();
    } catch (error) {
      alert(error.response?.data?.detail || "Failed to submit job");
    } finally {
      setSubmitting(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case "failed":
        return <XCircle className="w-5 h-5 text-red-500" />;
      case "processing":
        return <Loader className="w-5 h-5 text-blue-500 animate-spin" />;
      default:
        return <Clock className="w-5 h-5 text-yellow-500" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800";
      case "failed":
        return "bg-red-100 text-red-800";
      case "processing":
        return "bg-blue-100 text-blue-800";
      default:
        return "bg-yellow-100 text-yellow-800";
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Video className="w-8 h-8 text-indigo-600 mr-2" />
              <h1 className="text-xl font-bold text-gray-900">WebReel</h1>
            </div>

            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2 text-sm">
                <User className="w-4 h-4 text-gray-500" />
                <span className="text-gray-700">{user?.name}</span>
                <span className="px-2 py-1 bg-indigo-100 text-indigo-800 rounded text-xs font-medium">
                  {user?.tier}
                </span>
              </div>

              {isAdmin() && (
                <button
                  onClick={() => navigate("/admin")}
                  className="px-3 py-1 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm"
                >
                  Admin Panel
                </button>
              )}

              <button
                onClick={handleLogout}
                className="flex items-center space-x-1 text-gray-700 hover:text-gray-900"
              >
                <LogOut className="w-4 h-4" />
                <span className="text-sm">Logout</span>
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">Your Quota</h2>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-3xl font-bold text-indigo-600">
                  {user?.quota?.videos_used_this_month || 0} /{" "}
                  {user?.quota?.videos_per_month || 100}
                </p>
                <p className="text-sm text-gray-600 mt-1">Videos this month</p>
              </div>
              <div className="w-32 h-32">
                <svg viewBox="0 0 36 36" className="w-full h-full">
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="#e5e7eb"
                    strokeWidth="3"
                  />
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="#4f46e5"
                    strokeWidth="3"
                    strokeDasharray={`${((user?.quota?.videos_used_this_month || 0) / (user?.quota?.videos_per_month || 100)) * 100}, 100`}
                  />
                </svg>
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-900">My Jobs</h2>
          <div className="flex space-x-3">
            <button
              onClick={fetchJobs}
              className="flex items-center space-x-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Refresh</span>
            </button>
            <button
              onClick={() => setShowSubmitForm(true)}
              className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
            >
              <Plus className="w-4 h-4" />
              <span>New Job</span>
            </button>
          </div>
        </div>

        {showSubmitForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
              <h3 className="text-xl font-bold mb-4">Submit New Job</h3>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Task Description
                  </label>
                  <textarea
                    value={formData.task}
                    onChange={(e) => setFormData({ ...formData, task: e.target.value })}
                    required
                    rows={4}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Describe what you want to record..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Website URL
                  </label>
                  <input
                    type="url"
                    value={formData.url}
                    onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="https://example.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Narration (Optional)
                  </label>
                  <textarea
                    value={formData.narration}
                    onChange={(e) =>
                      setFormData({ ...formData, narration: e.target.value })
                    }
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Add voice narration to your video..."
                  />
                </div>

                <div className="flex space-x-3">
                  <button
                    type="button"
                    onClick={() => setShowSubmitForm(false)}
                    className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {submitting ? "Submitting..." : "Submit Job"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <Loader className="w-8 h-8 text-indigo-600 animate-spin mx-auto" />
            <p className="mt-2 text-gray-600">Loading jobs...</p>
          </div>
        ) : jobs.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <Video className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No jobs yet</h3>
            <p className="text-gray-600 mb-6">
              Create your first video by submitting a new job
            </p>
            <button
              onClick={() => setShowSubmitForm(true)}
              className="inline-flex items-center space-x-2 px-6 py-3 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
            >
              <Plus className="w-5 h-5" />
              <span>Submit Your First Job</span>
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Job ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Task
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {jobs.map((job) => (
                  <tr key={job.job_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                      {job.job_id?.substring(0, 8)}...
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <div className="max-w-xs truncate">{job.task}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(job.status)}
                        <span
                          className={`px-2 py-1 text-xs font-medium rounded ${getStatusColor(job.status)}`}
                        >
                          {job.status}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(job.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default UserDashboard;
