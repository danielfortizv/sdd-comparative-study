import React, { useEffect, useState, useCallback } from "react";
import { api, Review } from "../services/api";
import { useAuth } from "../context/AuthContext";
import { useToast } from "./FeedbackToast";

export const ModeratorDashboard: React.FC = () => {
  const { token, identifier } = useAuth();
  const { showToast } = useToast();

  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("pending");

  const fetchModerationReviews = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getModerationReviews(token);
      setReviews(data);
    } catch (err: any) {
      setError(err.message || "Failed to load reviews for moderation.");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchModerationReviews();
  }, [fetchModerationReviews]);

  const handleUpdateStatus = async (reviewId: string, status: string) => {
    if (!token) return;
    try {
      await api.updateReviewStatus(token, reviewId, status);
      showToast(`Review successfully ${status}!`, "success");
      // Update local state
      setReviews((prev) =>
        prev.map((r) => (r.review_id === reviewId ? { ...r, status } : r))
      );
    } catch (err: any) {
      showToast(err.message || `Failed to update status to ${status}.`, "error");
    }
  };

  if (identifier !== "moderator") {
    return (
      <div style={{ padding: "40px 20px", textAlign: "center" }}>
        <h2 style={{ color: "red" }}>Access Denied</h2>
        <p>You must be logged in as the moderator to view this page.</p>
      </div>
    );
  }

  const filteredReviews = reviews.filter((r) => r.status === activeTab);

  return (
    <div className="moderator-dashboard-container" style={{ padding: "20px 0" }} data-testid="moderator-dashboard">
      <h2 style={{ fontSize: "28px", marginBottom: "10px" }}>Moderation Dashboard</h2>
      <p style={{ color: "#666", marginBottom: "30px" }}>
        Review and manage customer product reviews to ensure safe and constructive content.
      </p>

      {/* Tabs */}
      <div className="dashboard-tabs" style={{ display: "flex", gap: "10px", marginBottom: "20px", borderBottom: "2px solid #ddd" }}>
        {["pending", "approved", "rejected"].map((tab) => {
          const count = reviews.filter((r) => r.status === tab).length;
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                padding: "10px 20px",
                cursor: "pointer",
                backgroundColor: activeTab === tab ? "#007bff" : "transparent",
                color: activeTab === tab ? "#fff" : "#333",
                border: "none",
                borderBottom: activeTab === tab ? "3px solid #0056b3" : "none",
                fontWeight: "bold",
                textTransform: "capitalize",
                fontSize: "14px",
                display: "flex",
                alignItems: "center",
                gap: "6px"
              }}
            >
              {tab} <span style={{ backgroundColor: activeTab === tab ? "#0056b3" : "#eee", color: activeTab === tab ? "#fff" : "#666", padding: "2px 6px", borderRadius: "10px", fontSize: "12px" }}>{count}</span>
            </button>
          );
        })}
      </div>

      {loading ? (
        <p>Loading queue...</p>
      ) : error ? (
        <p style={{ color: "red" }}>{error}</p>
      ) : filteredReviews.length === 0 ? (
        <div style={{ textAlign: "center", padding: "40px", border: "1px dashed #ccc", borderRadius: "8px", color: "#666" }}>
          No {activeTab} reviews found.
        </div>
      ) : (
        <div className="moderation-list" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {filteredReviews.map((rev) => (
            <div
              key={rev.review_id}
              className="moderation-card"
              style={{
                border: "1px solid #ddd",
                borderRadius: "8px",
                padding: "20px",
                backgroundColor: "#fff",
                boxShadow: "0 2px 4px rgba(0,0,0,0.05)",
                display: "flex",
                flexWrap: "wrap",
                gap: "20px"
              }}
              data-testid="moderation-card"
            >
              {rev.image_base64 && (
                <div className="moderation-review-image" style={{ flex: "0 0 150px" }}>
                  <img
                    src={rev.image_base64}
                    alt="Submitted product view"
                    style={{ maxWidth: "100%", maxHeight: "120px", objectFit: "contain", border: "1px solid #eee", borderRadius: "4px" }}
                  />
                </div>
              )}

              <div className="moderation-details" style={{ flex: "1 1 300px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "10px" }}>
                  <div>
                    <span style={{ fontWeight: "bold", fontSize: "15px" }}>User: {rev.user_id}</span>
                    <span style={{ color: "#666", fontSize: "13px", marginLeft: "15px" }}>Product: {rev.product_id}</span>
                  </div>
                  <span style={{ color: "#ffc107", fontWeight: "bold" }}>
                    {"★".repeat(rev.rating)}
                    {"☆".repeat(5 - rev.rating)}
                  </span>
                </div>

                <p style={{ color: "#333", fontSize: "14px", lineHeight: "1.5", margin: "0 0 15px 0" }}>{rev.comment}</p>

                <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                  {rev.status !== "approved" && (
                    <button
                      className="approve-btn"
                      onClick={() => handleUpdateStatus(rev.review_id, "approved")}
                      style={{
                        padding: "6px 12px",
                        cursor: "pointer",
                        backgroundColor: "#28a745",
                        color: "#fff",
                        border: "none",
                        borderRadius: "4px",
                        fontWeight: "bold",
                        fontSize: "13px"
                      }}
                    >
                      Approve
                    </button>
                  )}
                  {rev.status !== "rejected" && (
                    <button
                      className="reject-btn"
                      onClick={() => handleUpdateStatus(rev.review_id, "rejected")}
                      style={{
                        padding: "6px 12px",
                        cursor: "pointer",
                        backgroundColor: "#dc3545",
                        color: "#fff",
                        border: "none",
                        borderRadius: "4px",
                        fontWeight: "bold",
                        fontSize: "13px"
                      }}
                    >
                      Reject
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
export default ModeratorDashboard;