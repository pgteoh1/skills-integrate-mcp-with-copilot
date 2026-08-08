document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");
  const logoutButton = document.getElementById("logout-btn");
  const sessionMessage = document.getElementById("session-message");
  const emailInput = document.getElementById("email");
  const messageDiv = document.getElementById("message");

  let authState = {
    token: localStorage.getItem("authToken"),
    user: null,
  };

  function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.classList.remove("hidden");

    setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  function authHeaders() {
    if (!authState.token) {
      return {};
    }

    return {
      Authorization: `Bearer ${authState.token}`,
    };
  }

  function updateAuthUI() {
    if (!authState.user) {
      sessionMessage.textContent = "You are not logged in. Login is required for sign-up changes.";
      logoutButton.classList.add("hidden");
      loginForm.classList.remove("hidden");
      registerForm.classList.remove("hidden");
      signupForm.querySelector("button").disabled = true;
      emailInput.readOnly = false;
      return;
    }

    const roleLabel = authState.user.role.replace("_", " ");
    sessionMessage.textContent = `Logged in as ${authState.user.username} (${roleLabel})`;
    logoutButton.classList.remove("hidden");
    loginForm.classList.add("hidden");
    registerForm.classList.add("hidden");
    signupForm.querySelector("button").disabled = false;

    if (authState.user.role === "student") {
      emailInput.value = authState.user.email;
      emailInput.readOnly = true;
    } else {
      emailInput.readOnly = false;
    }
  }

  async function loadSession() {
    if (!authState.token) {
      updateAuthUI();
      return;
    }

    try {
      const response = await fetch("/auth/me", {
        headers: authHeaders(),
      });

      if (!response.ok) {
        throw new Error("Session expired");
      }

      authState.user = await response.json();
    } catch (error) {
      authState = { token: null, user: null };
      localStorage.removeItem("authToken");
    }

    updateAuthUI();
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        const canUnregisterAny =
          authState.user &&
          (authState.user.role === "club_admin" ||
            authState.user.role === "federation_admin");

        // Create participants HTML with delete icons instead of bullet points
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) => {
                      const canUnregisterOwn = authState.user && authState.user.email === email;
                      const showDeleteButton = canUnregisterAny || canUnregisterOwn;
                      const actionButton = showDeleteButton
                        ? `<button class="delete-btn" data-activity="${name}" data-email="${email}" title="Unregister">Unregister</button>`
                        : "";
                      return `<li><span class="participant-email">${email}</span>${actionButton}</li>`;
                    }
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
          headers: authHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const payload = {
      username: document.getElementById("login-username").value,
      password: document.getElementById("login-password").value,
    };

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const result = await response.json();
      if (!response.ok) {
        showMessage(result.detail || "Login failed", "error");
        return;
      }

      authState.token = result.access_token;
      authState.user = result.user;
      localStorage.setItem("authToken", result.access_token);

      loginForm.reset();
      updateAuthUI();
      fetchActivities();
      showMessage("Login successful", "success");
    } catch (error) {
      showMessage("Login failed. Please try again.", "error");
      console.error("Error logging in:", error);
    }
  });

  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const payload = {
      username: document.getElementById("register-username").value,
      email: document.getElementById("register-email").value,
      password: document.getElementById("register-password").value,
      role: document.getElementById("register-role").value,
    };

    try {
      const response = await fetch("/auth/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const result = await response.json();
      if (!response.ok) {
        showMessage(result.detail || "Registration failed", "error");
        return;
      }

      registerForm.reset();
      showMessage("Registration successful. Please log in.", "success");
    } catch (error) {
      showMessage("Registration failed. Please try again.", "error");
      console.error("Error registering:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    if (!authState.token) {
      return;
    }

    try {
      await fetch("/auth/logout", {
        method: "POST",
        headers: authHeaders(),
      });
    } catch (error) {
      console.error("Error during logout:", error);
    }

    authState = { token: null, user: null };
    localStorage.removeItem("authToken");
    updateAuthUI();
    fetchActivities();
    showMessage("Logged out", "info");
  });

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (!authState.token) {
      showMessage("Please log in first.", "error");
      return;
    }

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
          headers: authHeaders(),
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();

        if (authState.user && authState.user.role === "student") {
          emailInput.value = authState.user.email;
        }

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  // Initialize app
  loadSession();
  updateAuthUI();
  fetchActivities();
});
