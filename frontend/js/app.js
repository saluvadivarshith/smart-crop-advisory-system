/**
 * Main Frontend Application Logic — Smart Crop Advisory System
 * Connects all UI screens to the FastAPI backend without any hardcoded fake metrics.
 */

const API_BASE =
  window.location.protocol === "file:" || window.location.port === "5500" || window.location.port === "5501"
    ? "http://127.0.0.1:8000"
    : "";

const state = {
  currentUser: null,
  authToken: null,
  farms: [],
  activeFarm: null,
  cropResult: null,
  soilResult: null,
  weatherResult: null,
  riskResult: null,
  advisoryResult: null,
  calendarResult: null,
  sampleGallery: [],
  assessments: [],
  modelInfo: null,
  historyChart: null,
  map: null,
  mapTileMode: "satellite",
  satelliteLayer: null,
  streetLayer: null,
  mapMode: "draw",
  pinMarker: null,
  boundaryPoints: [],
  boundaryMarkers: [],
  boundaryPolygon: null,
  plotLengthM: null,
  plotWidthM: null,
};

const SOIL_PARAMS = [
  { id: "N", label: "Nitrogen (N)", unit: "kg/ha", placeholder: "e.g. 240" },
  { id: "P", label: "Phosphorus (P)", unit: "kg/ha", placeholder: "e.g. 18" },
  { id: "K", label: "Potassium (K)", unit: "kg/ha", placeholder: "e.g. 180" },
  { id: "OC", label: "Organic Carbon (OC)", unit: "%", placeholder: "e.g. 0.45" },
  { id: "pH", label: "Soil pH", unit: "2–12", placeholder: "e.g. 6.8" },
  { id: "EC", label: "Electrical Cond. (EC)", unit: "dS/m", placeholder: "e.g. 0.5" },
  { id: "S", label: "Sulphur (S)", unit: "mg/kg", placeholder: "e.g. 12" },
  { id: "Zn", label: "Zinc (Zn)", unit: "mg/kg", placeholder: "e.g. 0.55" },
  { id: "Fe", label: "Iron (Fe)", unit: "mg/kg", placeholder: "e.g. 5.2" },
  { id: "Cu", label: "Copper (Cu)", unit: "mg/kg", placeholder: "e.g. 0.6" },
  { id: "Mn", label: "Manganese (Mn)", unit: "mg/kg", placeholder: "e.g. 3.1" },
  { id: "B", label: "Boron (B)", unit: "mg/kg", placeholder: "e.g. 0.45" },
];

const SAMPLE_SOIL_DEFICIENT = {
  N: 195, P: 16, K: 165, OC: 0.38, pH: 7.7, EC: 0.55,
  S: 8.5, Zn: 0.48, Fe: 5.1, Cu: 0.65, Mn: 3.2, B: 0.42,
};

const SAMPLE_SOIL_HEALTHY = {
  N: 340, P: 22, K: 210, OC: 0.68, pH: 6.6, EC: 0.42,
  S: 14.0, Zn: 0.85, Fe: 6.4, Cu: 0.75, Mn: 4.0, B: 0.65,
};

const SAMPLE_SOIL_BLACK = {
  N: 230, P: 19, K: 290, OC: 0.48, pH: 8.2, EC: 0.75,
  S: 11.5, Zn: 0.52, Fe: 3.6, Cu: 0.70, Mn: 2.8, B: 0.48,
};

// -------------------------
// Utilities & Navigation
// -------------------------

function showToast(msg, duration = 4000) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.add("show");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove("show"), duration);
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function switchPage(pageId) {
  document.querySelectorAll("nav button").forEach((b) => {
    b.classList.toggle("active", b.dataset.page === pageId);
  });
  document.querySelectorAll(".page").forEach((p) => {
    p.classList.toggle("active", p.id === pageId);
  });
  if (pageId === "farm") {
    initFarmMap();
    setTimeout(() => {
      if (state.map) state.map.invalidateSize();
    }, 120);
  }
  if (pageId === "newfarm") {
    if (state.activeFarm && state.activeFarm.area_acres) {
      const nfArea = document.getElementById("nfArea");
      if (nfArea) nfArea.value = state.activeFarm.area_acres;
    }
    const wrap = document.getElementById("newFarmResultsWrap");
    if (wrap && !wrap.innerHTML.trim()) {
      window.runNewFarmWizard(false);
    }
  }
  if (pageId === "inputs") {
    if (state.activeFarm) {
      const inpArea = document.getElementById("inpArea");
      const inpCrop = document.getElementById("inpCrop");
      if (inpArea && state.activeFarm.area_acres) inpArea.value = state.activeFarm.area_acres;
      if (inpCrop && state.activeFarm.crop_name) inpCrop.value = state.activeFarm.crop_name;
    }
    const wrap = document.getElementById("inputsResultsWrap");
    if (wrap && !wrap.innerHTML.trim()) {
      window.runInputsAdvisor(false);
    }
  }
}

function getSelectedCrop() {
  const cropSelect = document.getElementById("cropSelect");
  if (cropSelect && cropSelect.value) return cropSelect.value;
  if (state.activeFarm && state.activeFarm.crop_name) return state.activeFarm.crop_name;
  return "Tomato";
}

function getSelectedStage() {
  const stageSelect = document.getElementById("stageSelect");
  return stageSelect && stageSelect.value ? stageSelect.value : "vegetative";
}

// -------------------------
// Initialization
// -------------------------

document.addEventListener("DOMContentLoaded", async () => {
  // Navigation buttons
  document.querySelectorAll("nav button").forEach((btn) => {
    btn.addEventListener("click", () => switchPage(btn.dataset.page));
  });

  // Language switcher
  document.querySelectorAll(".lang-btn").forEach((btn) => {
    btn.addEventListener("click", () => window.applyLanguage(btn.dataset.lang));
  });
  window.applyLanguage(window.currentLang);

  // Build Soil Health Card fields (blank by default so no fake values are submitted)
  renderSoilInputs();

  // Image preview listener
  const cropInput = document.getElementById("cropImage");
  if (cropInput) {
    cropInput.addEventListener("change", handleImagePreview);
  }

  // Sync crop select across pages
  const cropSelect = document.getElementById("cropSelect");
  const farmCropInput = document.getElementById("farmCrop");
  if (cropSelect) {
    cropSelect.addEventListener("change", () => {
      updateDashboardView();
    });
  }
  if (farmCropInput) {
    farmCropInput.addEventListener("change", () => {
      if (cropSelect) cropSelect.value = farmCropInput.value;
    });
  }

  // Enforce Sign-In gate first on page load
  await loadCurrentUser();
  loadModelStatus();
  loadSampleGallery();
});

// -------------------------
// Mandatory Farmer Login Gate & 2-Step Verification (Gmail / SMS OTP)
// -------------------------

let activeOtpChallengeId = null;

function authHeaders(extra = {}) {
  const h = { ...extra };
  if (state.authToken) {
    h["Authorization"] = `Bearer ${state.authToken}`;
  }
  return h;
}

function syncAuthLockState() {
  const modal = document.getElementById("authModal");
  const appShell = document.getElementById("appShell");
  if (state.currentUser && state.authToken) {
    document.body.classList.remove("auth-locked");
    if (appShell) appShell.style.display = "";
    if (modal) modal.classList.remove("show");
  } else {
    document.body.classList.add("auth-locked");
    if (appShell) appShell.style.display = "none";
    if (modal) modal.classList.add("show");
  }
}

async function loadCurrentUser() {
  // Always require explicit Sign In on fresh webpage access
  state.authToken = null;
  state.currentUser = null;
  localStorage.removeItem("cropsense_auth_token");
  syncAuthLockState();
  renderAuthSidebar();
}

function renderAuthSidebar() {
  const box = document.getElementById("authSidebarBox");
  if (!box) return;
  if (state.currentUser) {
    const u = state.currentUser;
    const contactParts = [u.phone ? `📱 ${u.phone}` : null, u.email ? `✉️ ${u.email}` : null]
      .filter(Boolean)
      .join(" · ");
    box.innerHTML = `
      <div class="auth-user-name">👨‍🌾 ${escapeHtml(u.full_name)}</div>
      <div class="auth-user-contact">${escapeHtml(contactParts)}</div>
      <button class="auth-btn-small logout" onclick="logoutFarmer()">🔒 Sign Out</button>
    `;
  } else {
    box.innerHTML = `
      <div class="auth-user-name">👤 Not Signed In</div>
      <div class="auth-user-contact">2-Step Verification Required</div>
      <button class="auth-btn-small" onclick="openAuthModal('signin')">🔑 Sign In / Sign Up</button>
    `;
  }
}

window.openAuthModal = function (tab = "signin") {
  const modal = document.getElementById("authModal");
  if (modal) modal.classList.add("show");
  backToAuthStep1();
  switchAuthTab(tab);
};

window.closeAuthModal = function () {
  // Never allow closing the modal if the user is not logged in
  if (!state.currentUser || !state.authToken) {
    showToast("Please Sign In or Sign Up with 2-Step Verification to access CropSense.");
    return;
  }
  const modal = document.getElementById("authModal");
  if (modal) modal.classList.remove("show");
};

window.switchAuthTab = function (tab) {
  const isSignup = tab === "signup";
  const tabSignin = document.getElementById("tabBtnSignin");
  const tabSignup = document.getElementById("tabBtnSignup");
  const formSignin = document.getElementById("signinForm");
  const formSignup = document.getElementById("signupForm");
  const alertBox = document.getElementById("authAlertBox");

  if (tabSignin) tabSignin.classList.toggle("active", !isSignup);
  if (tabSignup) tabSignup.classList.toggle("active", isSignup);
  if (formSignin) formSignin.style.display = isSignup ? "none" : "flex";
  if (formSignup) formSignup.style.display = isSignup ? "flex" : "none";
  if (alertBox) alertBox.innerHTML = "";
};

window.backToAuthStep1 = function () {
  activeOtpChallengeId = null;
  const s1 = document.getElementById("authStep1Wrap");
  const s2 = document.getElementById("authStep2Wrap");
  if (s1) s1.style.display = "block";
  if (s2) s2.style.display = "none";
};

function showOtpStep2(challengeData) {
  activeOtpChallengeId = challengeData.challenge_id;
  const s1 = document.getElementById("authStep1Wrap");
  const s2 = document.getElementById("authStep2Wrap");
  const titleEl = document.getElementById("otpStepTitle");
  const subEl = document.getElementById("otpStepSub");
  const alertEl = document.getElementById("otpAlertBox");
  const simEl = document.getElementById("otpSimulatedInbox");
  const codeIn = document.getElementById("otpCodeInput");

  if (s1) s1.style.display = "none";
  if (s2) s2.style.display = "block";
  if (alertEl) alertEl.innerHTML = "";
  if (codeIn) {
    codeIn.value = "";
    codeIn.focus();
  }

  const isEmail = challengeData.channel === "email";
  if (titleEl) {
    titleEl.textContent = isEmail
      ? "📧 Step 2: Gmail Verification Code"
      : "📱 Step 2: Mobile SMS Verification Code";
  }
  if (subEl) {
    subEl.textContent = isEmail
      ? `Enter the 6-digit verification code sent to your Gmail (${challengeData.destination})`
      : `Enter the 6-digit SMS verification code sent to +91-${challengeData.destination}`;
  }

  if (simEl) {
    if (challengeData.demo_otp_code) {
      const icon = isEmail ? "📧 Gmail Inbox Notification" : "💬 SMS Message Notification";
      simEl.innerHTML = `
        <div class="otp-sim-banner">
          <div><b>${icon} (${escapeHtml(challengeData.destination)}):</b></div>
          <div style="margin:6px 0">
            Your CropSense 2-Step verification code is:
            <span class="otp-sim-code">${escapeHtml(challengeData.demo_otp_code)}</span>
            <button type="button" class="secondary" style="padding:4px 10px;font-size:12px" onclick="fillSimulatedOtp('${escapeHtml(challengeData.demo_otp_code)}')">
              Auto-Fill Code
            </button>
          </div>
          <div class="sub" style="font-size:11px">${escapeHtml(challengeData.delivery_note || "")}</div>
        </div>
      `;
    } else {
      simEl.innerHTML = `
        <div class="alert green">
          <b>Live Code Dispatched:</b> ${escapeHtml(challengeData.delivery_note || "")}
        </div>
      `;
    }
  }
}

window.fillSimulatedOtp = function (code) {
  const el = document.getElementById("otpCodeInput");
  if (el) el.value = code;
};

window.prefillAndSwitchAuth = function (targetTab, identifier) {
  switchAuthTab(targetTab);
  const val = (identifier || "").trim();
  if (!val) return;
  if (targetTab === "signup") {
    if (val.includes("@")) {
      document.getElementById("signupEmail").value = val;
    } else {
      document.getElementById("signupPhone").value = val;
    }
  } else {
    document.getElementById("signinIdentifier").value = val;
  }
};

window.submitSignin = async function (event) {
  event.preventDefault();
  const identifier = (document.getElementById("signinIdentifier").value || "").trim();
  const password = document.getElementById("signinPassword").value || "";
  const alertBox = document.getElementById("authAlertBox");
  const btn = document.getElementById("btnSubmitSignin");

  if (btn) btn.disabled = true;
  if (alertBox) alertBox.innerHTML = "";

  try {
    const resp = await fetch(`${API_BASE}/api/auth/signin`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier, password }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      if (resp.status === 404) {
        if (alertBox) {
          alertBox.innerHTML = `
            <div class="alert">
              <b>New User Detected:</b> ${escapeHtml(data.detail)}<br>
              <button type="button" class="secondary" style="margin-top:8px" onclick="prefillAndSwitchAuth('signup', '${escapeHtml(identifier)}')">
                🌱 Continue to Sign Up with "${escapeHtml(identifier)}" →
              </button>
            </div>
          `;
        }
        return;
      }
      throw new Error(data.detail || "Sign in failed");
    }

    if (data.requires_otp) {
      showOtpStep2(data);
      showToast(`Step 1 verified! Enter the 6-digit ${data.channel === "email" ? "Gmail" : "SMS"} verification code.`);
      return;
    }
  } catch (err) {
    if (alertBox) {
      alertBox.innerHTML = `<div class="alert red">${escapeHtml(err.message)}</div>`;
    }
  } finally {
    if (btn) btn.disabled = false;
  }
};

window.submitSignup = async function (event) {
  event.preventDefault();
  const fullName = (document.getElementById("signupName").value || "").trim();
  const phone = (document.getElementById("signupPhone").value || "").trim() || null;
  const email = (document.getElementById("signupEmail").value || "").trim() || null;
  const chSel = (document.getElementById("signupChannel") || {}).value || "auto";
  const password = document.getElementById("signupPassword").value || "";
  const alertBox = document.getElementById("authAlertBox");
  const btn = document.getElementById("btnSubmitSignup");

  if (!phone && !email) {
    if (alertBox) {
      alertBox.innerHTML = `<div class="alert red">Please enter either your <b>Mobile Number</b> or your <b>Gmail Address</b> (or both) to create an account.</div>`;
    }
    return;
  }

  if (btn) btn.disabled = true;
  if (alertBox) alertBox.innerHTML = "";

  try {
    const resp = await fetch(`${API_BASE}/api/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        full_name: fullName,
        phone,
        email,
        password,
        preferred_channel: chSel === "auto" ? null : chSel,
      }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      if (resp.status === 409) {
        const match = (data.detail || "").match(/'([^']+)'/);
        const existingId = (match && match[1]) || phone || email || "";
        if (alertBox) {
          alertBox.innerHTML = `
            <div class="alert">
              <b>Account Already Exists:</b> ${escapeHtml(data.detail)}<br>
              <button type="button" class="secondary" style="margin-top:8px" onclick="prefillAndSwitchAuth('signin', '${escapeHtml(existingId)}')">
                🔑 Switch to Sign In with "${escapeHtml(existingId)}" →
              </button>
            </div>
          `;
        }
        return;
      }
      throw new Error(data.detail || "Sign up failed");
    }

    if (data.requires_otp) {
      showOtpStep2(data);
      showToast(`6-digit verification code sent via ${data.channel === "email" ? "Gmail" : "SMS"}!`);
      return;
    }
  } catch (err) {
    if (alertBox) {
      alertBox.innerHTML = `<div class="alert red">${escapeHtml(err.message)}</div>`;
    }
  } finally {
    if (btn) btn.disabled = false;
  }
};

window.submitVerifyOtp = async function (event) {
  event.preventDefault();
  const otpCode = (document.getElementById("otpCodeInput").value || "").trim();
  const alertEl = document.getElementById("otpAlertBox");
  const btn = document.getElementById("btnVerifyOtp");

  if (!activeOtpChallengeId) {
    backToAuthStep1();
    return;
  }

  if (btn) btn.disabled = true;
  if (alertEl) alertEl.innerHTML = "";

  try {
    const resp = await fetch(`${API_BASE}/api/auth/verify-otp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        challenge_id: activeOtpChallengeId,
        otp_code: otpCode,
      }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || "Invalid verification code");
    }

    state.authToken = data.token;
    state.currentUser = data.user;
    localStorage.setItem("cropsense_auth_token", data.token);
    syncAuthLockState();
    renderAuthSidebar();
    await loadFarms();
    await loadHistory();
    updateDashboardView();
    showToast(data.message || `2-Step Verification complete! Welcome, ${data.user.full_name}.`);
  } catch (err) {
    if (alertEl) {
      alertEl.innerHTML = `<div class="alert red">${escapeHtml(err.message)}</div>`;
    }
  } finally {
    if (btn) btn.disabled = false;
  }
};

window.resendOtpCode = async function () {
  if (!activeOtpChallengeId) return;
  try {
    const resp = await fetch(`${API_BASE}/api/auth/resend-otp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ challenge_id: activeOtpChallengeId }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Could not resend code");
    showOtpStep2(data);
    showToast("A fresh 6-digit verification code has been sent!");
  } catch (err) {
    showToast(err.message);
  }
};

window.saveSenderConfig = async function () {
  const smtpEmail = (document.getElementById("cfgSmtpEmail").value || "").trim();
  const smtpPass = (document.getElementById("cfgSmtpPass").value || "").trim();
  const smsKey = (document.getElementById("cfgSmsKey").value || "").trim();
  const statusEl = document.getElementById("cfgSenderStatus");

  try {
    const resp = await fetch(`${API_BASE}/api/auth/sender-settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        smtp_email: smtpEmail || null,
        smtp_app_password: smtpPass || null,
        fast2sms_api_key: smsKey || null,
      }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error("Failed to save sender config");
    if (statusEl) {
      statusEl.textContent = `Saved! Gmail SMTP: ${data.smtp_configured ? "Active (" + data.smtp_email + ")" : "Not set"} · SMS Gateway: ${data.sms_configured ? "Active" : "Simulated"}`;
    }
    showToast("Live OTP sender settings updated!");
  } catch (err) {
    showToast(err.message);
  }
};

window.logoutFarmer = async function () {
  try {
    await fetch(`${API_BASE}/api/auth/logout`, {
      method: "POST",
      headers: authHeaders(),
    });
  } catch (e) {
    // ignore network error on logout
  }
  state.authToken = null;
  state.currentUser = null;
  localStorage.removeItem("cropsense_auth_token");
  backToAuthStep1();
  syncAuthLockState();
  renderAuthSidebar();
  showToast("Signed out. Please sign in with 2-Step Verification to continue.");
};

function renderSoilInputs() {
  const container = document.getElementById("soilFields");
  if (!container) return;
  container.innerHTML = SOIL_PARAMS.map(
    (p) => `
    <label for="soil_${p.id}">
      ${escapeHtml(p.label)} <span class="unit-hint">(${escapeHtml(p.unit)})</span>
      <input id="soil_${p.id}" type="number" step="any" min="0" placeholder="${escapeHtml(p.placeholder)}">
    </label>`
  ).join("");
}

function fillSoilSample(sampleObj) {
  SOIL_PARAMS.forEach((p) => {
    const el = document.getElementById(`soil_${p.id}`);
    if (el) el.value = sampleObj[p.id] !== undefined ? sampleObj[p.id] : "";
  });
  showToast("Sample Soil Health Card values loaded. Click 'Analyze Soil Health' to evaluate.");
}

function clearSoilInputs() {
  SOIL_PARAMS.forEach((p) => {
    const el = document.getElementById(`soil_${p.id}`);
    if (el) el.value = "";
  });
  state.soilResult = null;
  const resEl = document.getElementById("soilResult");
  if (resEl) resEl.innerHTML = "";
  updateDashboardView();
}

// -------------------------
// ML Model Status
// -------------------------

async function loadModelStatus() {
  const banner = document.getElementById("modelStatusBanner");
  try {
    const resp = await fetch(`${API_BASE}/api/crop/model-info`);
    if (!resp.ok) throw new Error("Failed to fetch model info");
    const info = await resp.json();
    state.modelInfo = info;

    if (!banner) return;
    if (info.available) {
      const accText = info.test_accuracy
        ? `Test Accuracy: ${(info.test_accuracy * 100).toFixed(1)}%`
        : info.best_val_accuracy
        ? `Validation Accuracy: ${(info.best_val_accuracy * 100).toFixed(1)}%`
        : "";
      banner.className = "alert green";
      banner.innerHTML = `
        <b>ML Disease Classifier Ready (${escapeHtml(info.arch)}, ${info.num_classes} classes)</b>
        ${accText ? ` · <span>${escapeHtml(accText)}</span>` : ""}
        <br><span class="sub">Supported leaf crops: ${escapeHtml((info.supported_crops || []).join(", "))}</span>
      `;
    } else {
      banner.className = "alert";
      banner.innerHTML = `
        <b>ML Model Weights Not Yet Trained:</b> ${escapeHtml(info.message)}
      `;
    }
  } catch (err) {
    if (banner) {
      banner.className = "alert red";
      banner.textContent = "Backend server is not reachable. Start FastAPI with: uvicorn backend.main:app --reload";
    }
  }
}

// -------------------------
// Farm Profile & Location
// -------------------------

async function loadFarms() {
  try {
    const resp = await fetch(`${API_BASE}/api/farms`, { headers: authHeaders() });
    if (!resp.ok) return;
    const data = await resp.json();
    state.farms = data.farms || [];

    const savedId = Number(localStorage.getItem("cropsense_active_farm_id"));
    const match = state.farms.find((f) => f.id === savedId) || state.farms[0] || null;
    if (match) {
      await setActiveFarm(match, false);
    } else {
      renderActiveFarmBanner();
      renderSavedFarmsList();
    }
  } catch (err) {
    console.error("Could not load farms:", err);
  }
}

async function setActiveFarm(farm, notify = true) {
  state.activeFarm = farm;
  if (farm) {
    localStorage.setItem("cropsense_active_farm_id", String(farm.id));
    const cropSelect = document.getElementById("cropSelect");
    if (cropSelect && farm.crop_name) {
      cropSelect.value = farm.crop_name;
    }
    // Populate form fields with active farm
    document.getElementById("farmName").value = farm.farm_name || "";
    document.getElementById("farmVillage").value = farm.village || "";
    document.getElementById("farmDistrict").value = farm.district || "";
    document.getElementById("farmState").value = farm.state || "";
    document.getElementById("farmLat").value = farm.latitude ?? "";
    document.getElementById("farmLon").value = farm.longitude ?? "";
    if (farm.crop_name) document.getElementById("farmCrop").value = farm.crop_name;
    const sowEl = document.getElementById("farmSowingDate");
    if (sowEl) sowEl.value = farm.sowing_date || "";
    document.getElementById("farmArea").value = farm.area_acres ?? "";
    document.getElementById("manualLength").value = farm.plot_length_m ?? "";
    document.getElementById("manualWidth").value = farm.plot_width_m ?? "";
    document.getElementById("manualDimUnit").value = "m";
    state.plotLengthM = farm.plot_length_m ?? null;
    state.plotWidthM = farm.plot_width_m ?? null;

    initFarmMap();
    if (Array.isArray(farm.boundary_geojson) && farm.boundary_geojson.length >= 3) {
      loadBoundaryOnMap(farm.boundary_geojson);
    } else if (farm.latitude != null && farm.longitude != null) {
      clearBoundaryPolygon(false);
      centerMapAndSetPin(farm.latitude, farm.longitude, 16);
      if (farm.area_acres) {
        updateDimensionSummaryDisplay(farm.area_acres * 4046.8564224, farm.plot_length_m, farm.plot_width_m);
      }
    }
  } else {
    localStorage.removeItem("cropsense_active_farm_id");
  }

  renderActiveFarmBanner();
  renderSavedFarmsList();

  if (farm && farm.latitude != null && farm.longitude != null) {
    await loadWeather(farm.latitude, farm.longitude, false);
  }
  await loadHistory();
  updateDashboardView();
  if (notify && farm) {
    showToast(`Active farm set to "${farm.farm_name}" (${farm.village || "Coords saved"})`);
  }
}

function renderActiveFarmBanner() {
  const sidebarBox = document.getElementById("activeFarmSummary");
  const dashFarmBadge = document.getElementById("dashFarmBadge");
  const weatherLocLabel = document.getElementById("weatherLocationLabel");

  if (!state.activeFarm) {
    if (sidebarBox) {
      sidebarBox.innerHTML = `<span class="sub">No farm selected yet.</span>`;
    }
    if (dashFarmBadge) {
      dashFarmBadge.className = "badge neutral";
      dashFarmBadge.textContent = "No farm selected — set location in Farm Profile";
    }
    if (weatherLocLabel) {
      weatherLocLabel.textContent = "Select or create a farm profile to load field weather.";
    }
    return;
  }

  const f = state.activeFarm;
  const locParts = [f.village, f.district, f.state].filter(Boolean).join(", ");
  const coordStr = `${Number(f.latitude).toFixed(3)}°N, ${Number(f.longitude).toFixed(3)}°E`;
  const areaBadge = f.area_acres ? ` · ${Number(f.area_acres).toFixed(2)} ac (${(f.area_acres * 40).toFixed(1)} guntas)` : "";

  if (sidebarBox) {
    sidebarBox.innerHTML = `
      <strong>${escapeHtml(f.farm_name)}</strong>
      <div class="sub">${escapeHtml(locParts || coordStr)}</div>
      <div class="sub">Crop: <b>${escapeHtml(f.crop_name || getSelectedCrop())}</b>${escapeHtml(areaBadge)}</div>
    `;
  }
  if (dashFarmBadge) {
    dashFarmBadge.className = "badge";
    dashFarmBadge.textContent = `${f.farm_name} · ${locParts || coordStr}${areaBadge}`;
  }
  if (weatherLocLabel) {
    weatherLocLabel.textContent = `Weather for ${f.farm_name} (${locParts || coordStr})`;
  }
}

function renderSavedFarmsList() {
  const wrap = document.getElementById("savedFarmsList");
  if (!wrap) return;

  if (!state.farms.length) {
    wrap.innerHTML = `<div class="empty-state">No saved farms yet. Use GPS or search your village above and click "Save Farm Profile".</div>`;
    return;
  }

  wrap.innerHTML = `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Farm Name</th>
            <th>Village / District / State</th>
            <th>Coordinates</th>
            <th>Land Size & Dimensions</th>
            <th>Crop</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${state.farms
            .map((f) => {
              const isAct = state.activeFarm && state.activeFarm.id === f.id;
              const loc = [f.village, f.district, f.state].filter(Boolean).join(", ") || "—";
              const dimText =
                f.plot_length_m && f.plot_width_m
                  ? ` (${Number(f.plot_length_m).toFixed(0)}m × ${Number(f.plot_width_m).toFixed(0)}m)`
                  : Array.isArray(f.boundary_geojson) && f.boundary_geojson.length >= 3
                  ? ` (${f.boundary_geojson.length}-corner map polygon)`
                  : "";
              const sizeStr = f.area_acres
                ? `<b>${Number(f.area_acres).toFixed(2)} ac</b> / ${(f.area_acres * 40).toFixed(1)} guntas${escapeHtml(dimText)}`
                : "—";
              return `
                <tr>
                  <td><b>${escapeHtml(f.farm_name)}</b> ${isAct ? '<span class="pill ok">Active</span>' : ""}</td>
                  <td>${escapeHtml(loc)}</td>
                  <td>${Number(f.latitude).toFixed(4)}, ${Number(f.longitude).toFixed(4)}</td>
                  <td>${sizeStr}</td>
                  <td>${escapeHtml(f.crop_name || "—")}</td>
                  <td>
                    <button class="secondary" onclick="selectFarmById(${f.id})">Select</button>
                    <button class="danger-btn" onclick="deleteFarmById(${f.id})">Delete</button>
                  </td>
                </tr>
              `;
            })
            .join("")}
        </tbody>
      </table>
    </div>
  `;
}

window.selectFarmById = async function (id) {
  const farm = state.farms.find((f) => f.id === id);
  if (farm) await setActiveFarm(farm, true);
};

window.deleteFarmById = async function (id) {
  try {
    const resp = await fetch(`${API_BASE}/api/farms/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error("Failed to delete farm");
    if (state.activeFarm && state.activeFarm.id === id) {
      state.activeFarm = null;
    }
    await loadFarms();
    showToast("Farm profile deleted.");
  } catch (err) {
    showToast("Could not delete farm profile.");
  }
};

window.useCurrentGpsLocation = function () {
  const statusEl = document.getElementById("geoStatus");
  if (!navigator.geolocation) {
    if (statusEl) statusEl.textContent = "Geolocation is not supported by this browser. Use manual village search.";
    return;
  }
  if (statusEl) statusEl.textContent = "Requesting GPS coordinates from your device...";

  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      const lat = Number(pos.coords.latitude.toFixed(5));
      const lon = Number(pos.coords.longitude.toFixed(5));
      document.getElementById("farmLat").value = lat;
      document.getElementById("farmLon").value = lon;
      centerMapAndSetPin(lat, lon, 17);
      if (statusEl) statusEl.textContent = `GPS coordinates captured (${lat}, ${lon}). Looking up village name...`;

      try {
        const resp = await fetch(`${API_BASE}/api/location/reverse?latitude=${lat}&longitude=${lon}`);
        if (resp.ok) {
          const place = await resp.json();
          if (place.village) document.getElementById("farmVillage").value = place.village;
          if (place.district) document.getElementById("farmDistrict").value = place.district;
          if (place.state) document.getElementById("farmState").value = place.state;
          if (!document.getElementById("farmName").value && place.village) {
            document.getElementById("farmName").value = `${place.village} Plot`;
          }
          if (statusEl) statusEl.textContent = `Located: ${place.display_name || `${lat}, ${lon}`}`;
        }
      } catch (e) {
        if (statusEl) statusEl.textContent = `GPS coordinates set (${lat}, ${lon}). Fill village name below and save.`;
      }
    },
    (err) => {
      if (statusEl) {
        statusEl.textContent =
          "GPS permission was denied or unavailable. Please search your village or town name manually in the box beside it.";
      }
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
};

window.searchVillageLocation = async function () {
  const query = (document.getElementById("locationSearchInput").value || "").trim();
  const listEl = document.getElementById("locationSearchResults");
  if (query.length < 2) {
    showToast("Please type at least 2 letters of your village, mandal, or town name.");
    return;
  }
  listEl.classList.add("show");
  listEl.innerHTML = `<div class="location-item">Searching for "${escapeHtml(query)}"...</div>`;

  try {
    const resp = await fetch(`${API_BASE}/api/location/search?q=${encodeURIComponent(query)}&country=in`);
    if (!resp.ok) throw new Error("Location search failed");
    const data = await resp.json();
    const results = data.results || [];
    if (!results.length) {
      listEl.innerHTML = `<div class="location-item">No matching village or town found. Try searching the nearest town or district name.</div>`;
      return;
    }

    listEl.innerHTML = results
      .map(
        (r, i) => `
      <div class="location-item" data-idx="${i}">
        <div>
          <b>${escapeHtml(r.village || r.display_name)}</b>
          <div class="sub">${escapeHtml(r.display_name)}</div>
        </div>
        <span class="pill ok">Select</span>
      </div>`
      )
      .join("");

    listEl.querySelectorAll(".location-item").forEach((item) => {
      item.addEventListener("click", () => {
        const picked = results[Number(item.dataset.idx)];
        document.getElementById("farmVillage").value = picked.village || "";
        document.getElementById("farmDistrict").value = picked.district || "";
        document.getElementById("farmState").value = picked.state || "";
        document.getElementById("farmLat").value = Number(picked.latitude).toFixed(5);
        document.getElementById("farmLon").value = Number(picked.longitude).toFixed(5);
        centerMapAndSetPin(Number(picked.latitude), Number(picked.longitude), 16);
        if (!document.getElementById("farmName").value) {
          document.getElementById("farmName").value = `${picked.village || "Farm"} Field`;
        }
        listEl.classList.remove("show");
        showToast(`Selected location: ${picked.village || picked.display_name}. Now tap your plot corners on the map below!`);
      });
    });
  } catch (err) {
    listEl.innerHTML = `<div class="location-item">Location search service unavailable. You can still enter latitude and longitude directly.</div>`;
  }
};

window.voiceSearchVillage = function () {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  const btn = document.getElementById("btnVoiceVillage");
  if (!SpeechRec) {
    showToast("Voice recognition is supported in Chrome and Edge browsers. Please type your village name.");
    return;
  }

  const rec = new SpeechRec();
  const langMap = { te: "te-IN", hi: "hi-IN", en: "en-IN" };
  rec.lang = langMap[window.currentLang] || "en-IN";
  rec.interimResults = false;
  rec.maxAlternatives = 1;

  if (btn) {
    btn.classList.add("listening");
    btn.textContent = "🎙️ Listening...";
  }
  showToast("Speak your village, mandal, or district name now...");

  rec.onresult = (event) => {
    const transcript = event.results[0][0].transcript || "";
    const input = document.getElementById("locationSearchInput");
    if (input) {
      input.value = transcript.replace(/[.,!?]/g, "").trim();
      searchVillageLocation();
    }
  };

  rec.onerror = () => {
    showToast("Could not hear village name clearly. Please try again or type it.");
  };

  rec.onend = () => {
    if (btn) {
      btn.classList.remove("listening");
      btn.textContent = "🎙️ Speak";
    }
  };

  rec.start();
};

window.saveFarmProfile = async function () {
  const farmName = (document.getElementById("farmName").value || "").trim();
  const village = (document.getElementById("farmVillage").value || "").trim() || null;
  const district = (document.getElementById("farmDistrict").value || "").trim() || null;
  const stateName = (document.getElementById("farmState").value || "").trim() || null;
  const latStr = document.getElementById("farmLat").value;
  const lonStr = document.getElementById("farmLon").value;
  const cropName = document.getElementById("farmCrop").value || "Tomato";
  const sowingDateEl = document.getElementById("farmSowingDate");
  const sowingDate = sowingDateEl && sowingDateEl.value ? sowingDateEl.value : null;
  const areaStr = document.getElementById("farmArea").value;

  if (!farmName) {
    showToast("Please enter a Farm Name (for example, 'North Plot' or 'Raju Farm').");
    return;
  }
  if (latStr === "" || lonStr === "") {
    showToast("Please select your farm location using GPS or Village Search first.");
    return;
  }

  const lat = parseFloat(latStr);
  const lon = parseFloat(lonStr);
  if (Number.isNaN(lat) || Number.isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
    showToast("Invalid coordinates. Latitude must be -90..90 and Longitude -180..180.");
    return;
  }

  const payload = {
    farm_name: farmName,
    village,
    district,
    state: stateName,
    latitude: lat,
    longitude: lon,
    crop_name: cropName,
    sowing_date: sowingDate,
    area_acres: areaStr ? parseFloat(areaStr) : null,
    plot_length_m: state.plotLengthM ? Number(state.plotLengthM.toFixed(1)) : null,
    plot_width_m: state.plotWidthM ? Number(state.plotWidthM.toFixed(1)) : null,
    boundary_geojson:
      state.boundaryPoints && state.boundaryPoints.length >= 3
        ? state.boundaryPoints.map((pt) => [Number(pt[0].toFixed(6)), Number(pt[1].toFixed(6))])
        : null,
  };

  try {
    const resp = await fetch(`${API_BASE}/api/farms`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}));
      throw new Error(errData.detail || "Could not save farm");
    }
    const created = await resp.json();
    await loadFarms();
    await setActiveFarm(created, true);
  } catch (err) {
    showToast(`Error saving farm: ${err.message}`);
  }
};

// -------------------------
// Interactive Land Boundary Map & Manual Dimension Calculator
// -------------------------

function initFarmMap() {
  const mapEl = document.getElementById("farmMap");
  if (!mapEl || typeof L === "undefined") return;
  if (state.map) return;

  const startLat = state.activeFarm ? state.activeFarm.latitude : 17.9689;
  const startLon = state.activeFarm ? state.activeFarm.longitude : 79.5941;
  const startZoom = state.activeFarm ? 16 : 6;

  state.map = L.map("farmMap", { center: [startLat, startLon], zoom: startZoom });

  // Satellite imagery (Esri World Imagery — free, no key required) + Street overlay
  state.satelliteLayer = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    {
      maxZoom: 19,
      attribution: "Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics",
    }
  );
  state.streetLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  });

  state.satelliteLayer.addTo(state.map);
  state.mapTileMode = "satellite";

  state.map.on("click", (e) => {
    const lat = Number(e.latlng.lat.toFixed(6));
    const lon = Number(e.latlng.lng.toFixed(6));
    if (state.mapMode === "pin") {
      document.getElementById("farmLat").value = lat;
      document.getElementById("farmLon").value = lon;
      centerMapAndSetPin(lat, lon, state.map.getZoom());
      showToast(`Pin set at ${lat}, ${lon}`);
    } else {
      addBoundaryVertex(lat, lon);
    }
  });
}

window.setMapMode = function (mode) {
  state.mapMode = mode === "pin" ? "pin" : "draw";
  const pinBtn = document.getElementById("modePinBtn");
  const drawBtn = document.getElementById("modeDrawBtn");
  if (pinBtn) pinBtn.classList.toggle("active", state.mapMode === "pin");
  if (drawBtn) drawBtn.classList.toggle("active", state.mapMode === "draw");
  showToast(
    state.mapMode === "draw"
      ? "Draw Mode: Tap 3 or more corners of your land on the map."
      : "Pin Mode: Tap anywhere on the map to set farm coordinates."
  );
};

window.toggleMapLayer = function () {
  initFarmMap();
  if (!state.map) return;
  const btn = document.getElementById("btnToggleTile");
  if (state.mapTileMode === "satellite") {
    state.map.removeLayer(state.satelliteLayer);
    state.streetLayer.addTo(state.map);
    state.mapTileMode = "street";
    if (btn) btn.textContent = "🛰️ Switch to Satellite View";
  } else {
    state.map.removeLayer(state.streetLayer);
    state.satelliteLayer.addTo(state.map);
    state.mapTileMode = "satellite";
    if (btn) btn.textContent = "🗺️ Switch to Street Map";
  }
};

function centerMapAndSetPin(lat, lon, zoom = 16) {
  initFarmMap();
  if (!state.map) return;
  state.map.setView([lat, lon], zoom);
  if (state.pinMarker) {
    state.pinMarker.setLatLng([lat, lon]);
  } else {
    state.pinMarker = L.marker([lat, lon]).addTo(state.map);
  }
}

function addBoundaryVertex(lat, lon) {
  initFarmMap();
  if (!state.map) return;
  state.boundaryPoints.push([lat, lon]);
  redrawBoundaryOnMap();
}

window.undoLastBoundaryPoint = function () {
  if (!state.boundaryPoints.length) return;
  state.boundaryPoints.pop();
  redrawBoundaryOnMap();
};

window.clearBoundaryPolygon = function (resetFields = true) {
  state.boundaryPoints = [];
  if (state.map) {
    state.boundaryMarkers.forEach((m) => state.map.removeLayer(m));
    if (state.boundaryPolygon) state.map.removeLayer(state.boundaryPolygon);
  }
  state.boundaryMarkers = [];
  state.boundaryPolygon = null;
  if (resetFields) {
    updateDimensionSummaryDisplay(0, null, null);
  }
};

function loadBoundaryOnMap(points) {
  initFarmMap();
  clearBoundaryPolygon(false);
  state.boundaryPoints = points.map((p) => [Number(p[0]), Number(p[1])]);
  redrawBoundaryOnMap(true);
}

function redrawBoundaryOnMap(fitBounds = false) {
  if (!state.map) return;
  state.boundaryMarkers.forEach((m) => state.map.removeLayer(m));
  state.boundaryMarkers = [];
  if (state.boundaryPolygon) {
    state.map.removeLayer(state.boundaryPolygon);
    state.boundaryPolygon = null;
  }

  state.boundaryPoints.forEach((pt, idx) => {
    const marker = L.circleMarker(pt, {
      radius: 6,
      color: "#ffffff",
      weight: 2,
      fillColor: "#3b6e52",
      fillOpacity: 1,
    })
      .bindTooltip(`Corner ${idx + 1}`, { direction: "top" })
      .addTo(state.map);
    state.boundaryMarkers.push(marker);
  });

  if (state.boundaryPoints.length >= 2) {
    state.boundaryPolygon = L.polygon(state.boundaryPoints, {
      color: "#52b788",
      weight: 3,
      fillColor: "#52b788",
      fillOpacity: 0.32,
    }).addTo(state.map);

    if (fitBounds) {
      state.map.fitBounds(state.boundaryPolygon.getBounds(), { padding: [24, 24], maxZoom: 18 });
    }
  }

  if (state.boundaryPoints.length === 1) {
    const [lat, lon] = state.boundaryPoints[0];
    document.getElementById("farmLat").value = lat.toFixed(5);
    document.getElementById("farmLon").value = lon.toFixed(5);
    updateDimensionSummaryDisplay(0, null, null);
  } else if (state.boundaryPoints.length >= 3) {
    const metrics = computePolygonGeodesicMetrics(state.boundaryPoints);
    document.getElementById("farmLat").value = metrics.centroidLat.toFixed(5);
    document.getElementById("farmLon").value = metrics.centroidLon.toFixed(5);
    const acres = metrics.areaSqMeters / 4046.8564224;
    document.getElementById("farmArea").value = acres.toFixed(2);
    document.getElementById("manualLength").value = metrics.lengthM.toFixed(1);
    document.getElementById("manualWidth").value = metrics.widthM.toFixed(1);
    document.getElementById("manualDimUnit").value = "m";
    state.plotLengthM = metrics.lengthM;
    state.plotWidthM = metrics.widthM;
    updateDimensionSummaryDisplay(metrics.areaSqMeters, metrics.lengthM, metrics.widthM);
  }
}

/**
 * Compute geodesic area (m²), centroid, and bounding length × width (m)
 * of a lat/lon polygon using local equirectangular projection around the centroid.
 */
function computePolygonGeodesicMetrics(points) {
  const R = 6378137.0; // WGS84 Earth radius in meters
  const n = points.length;
  const meanLat = points.reduce((s, p) => s + p[0], 0) / n;
  const meanLon = points.reduce((s, p) => s + p[1], 0) / n;
  const cosLat = Math.cos((meanLat * Math.PI) / 180.0);

  // Convert each vertex to local (x, y) in meters relative to (meanLat, meanLon)
  const xy = points.map(([lat, lon]) => {
    const x = ((lon - meanLon) * Math.PI / 180.0) * R * cosLat;
    const y = ((lat - meanLat) * Math.PI / 180.0) * R;
    return [x, y];
  });

  // Shoelace formula for polygon area in m²
  let area2 = 0;
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (let i = 0; i < n; i++) {
    const [x1, y1] = xy[i];
    const [x2, y2] = xy[(i + 1) % n];
    area2 += x1 * y2 - x2 * y1;
    if (x1 < minX) minX = x1;
    if (x1 > maxX) maxX = x1;
    if (y1 < minY) minY = y1;
    if (y1 > maxY) maxY = y1;
  }
  const areaSqMeters = Math.abs(area2) / 2.0;
  const spanX = Math.max(1, maxX - minX);
  const spanY = Math.max(1, maxY - minY);
  const lengthM = Math.max(spanX, spanY);
  const widthM = Math.min(spanX, spanY);

  return {
    areaSqMeters,
    centroidLat: meanLat,
    centroidLon: meanLon,
    lengthM,
    widthM,
  };
}

function updateDimensionSummaryDisplay(areaSqMeters, lengthM = null, widthM = null) {
  const acres = areaSqMeters / 4046.8564224;
  const guntas = acres * 40.0;
  const hectares = areaSqMeters / 10000.0;

  const acEl = document.getElementById("dimAcres");
  const guEl = document.getElementById("dimGuntas");
  const haEl = document.getElementById("dimHectares");
  const sqmEl = document.getElementById("dimSqMeters");

  if (acEl) acEl.textContent = `${acres.toFixed(2)} ac`;
  if (guEl) guEl.textContent = `${guntas.toFixed(1)} guntas`;
  if (haEl) haEl.textContent = `${hectares.toFixed(2)} ha`;
  if (sqmEl) {
    const dimPart =
      lengthM && widthM ? `${Math.round(lengthM)}m × ${Math.round(widthM)}m (${Math.round(areaSqMeters)} m²)` : `${Math.round(areaSqMeters)} m²`;
    sqmEl.textContent = dimPart;
  }
}

window.calculateManualDimensions = function () {
  const lenVal = parseFloat(document.getElementById("manualLength").value);
  const widVal = parseFloat(document.getElementById("manualWidth").value);
  const unit = document.getElementById("manualDimUnit").value || "m";

  if (Number.isNaN(lenVal) || Number.isNaN(widVal) || lenVal <= 0 || widVal <= 0) {
    return;
  }

  const factorToMeters = unit === "ft" ? 0.3048 : unit === "yd" ? 0.9144 : 1.0;
  const lenM = lenVal * factorToMeters;
  const widM = widVal * factorToMeters;
  const areaSqMeters = lenM * widM;
  const acres = areaSqMeters / 4046.8564224;

  state.plotLengthM = lenM;
  state.plotWidthM = widM;

  document.getElementById("farmArea").value = acres.toFixed(2);
  document.getElementById("inputGuntas").value = (acres * 40).toFixed(1);
  document.getElementById("inputCents").value = (acres * 100).toFixed(1);
  updateDimensionSummaryDisplay(areaSqMeters, lenM, widM);

  const note = document.getElementById("manualCalcNote");
  if (note) {
    note.textContent = `Calculated: ${lenM.toFixed(1)}m × ${widM.toFixed(1)}m = ${Math.round(areaSqMeters)} m² (${acres.toFixed(2)} Acres / ${(acres * 40).toFixed(1)} Guntas).`;
  }
};

window.applyManualPlotToMap = function () {
  calculateManualDimensions();
  if (!state.plotLengthM || !state.plotWidthM) {
    showToast("Please enter Plot Length and Plot Width first.");
    return;
  }

  let lat = parseFloat(document.getElementById("farmLat").value);
  let lon = parseFloat(document.getElementById("farmLon").value);
  if (Number.isNaN(lat) || Number.isNaN(lon)) {
    if (state.activeFarm) {
      lat = state.activeFarm.latitude;
      lon = state.activeFarm.longitude;
    } else {
      lat = 17.9689;
      lon = 79.5941;
      document.getElementById("farmLat").value = lat;
      document.getElementById("farmLon").value = lon;
    }
  }

  // Build a rectangle centered on (lat, lon) with plotLengthM (East-West) and plotWidthM (North-South)
  const R = 6378137.0;
  const halfLen = state.plotLengthM / 2.0;
  const halfWid = state.plotWidthM / 2.0;
  const dLat = (halfWid / R) * (180.0 / Math.PI);
  const dLon = (halfLen / (R * Math.cos((lat * Math.PI) / 180.0))) * (180.0 / Math.PI);

  const rectPoints = [
    [lat + dLat, lon - dLon],
    [lat + dLat, lon + dLon],
    [lat - dLat, lon + dLon],
    [lat - dLat, lon - dLon],
  ];
  loadBoundaryOnMap(rectPoints);
  showToast(`Drawn ${Math.round(state.plotLengthM)}m × ${Math.round(state.plotWidthM)}m plot boundary on the map!`);
};

window.convertFromGuntas = function () {
  const guntas = parseFloat(document.getElementById("inputGuntas").value);
  if (Number.isNaN(guntas) || guntas <= 0) return;
  const acres = guntas / 40.0;
  const sqMeters = acres * 4046.8564224;
  const sideM = Math.sqrt(sqMeters);
  document.getElementById("farmArea").value = acres.toFixed(2);
  document.getElementById("inputCents").value = (acres * 100).toFixed(1);
  document.getElementById("manualLength").value = sideM.toFixed(1);
  document.getElementById("manualWidth").value = sideM.toFixed(1);
  document.getElementById("manualDimUnit").value = "m";
  state.plotLengthM = sideM;
  state.plotWidthM = sideM;
  updateDimensionSummaryDisplay(sqMeters, sideM, sideM);
};

window.convertFromCents = function () {
  const cents = parseFloat(document.getElementById("inputCents").value);
  if (Number.isNaN(cents) || cents <= 0) return;
  const acres = cents / 100.0;
  const sqMeters = acres * 4046.8564224;
  const sideM = Math.sqrt(sqMeters);
  document.getElementById("farmArea").value = acres.toFixed(2);
  document.getElementById("inputGuntas").value = (acres * 40).toFixed(1);
  document.getElementById("manualLength").value = sideM.toFixed(1);
  document.getElementById("manualWidth").value = sideM.toFixed(1);
  document.getElementById("manualDimUnit").value = "m";
  state.plotLengthM = sideM;
  state.plotWidthM = sideM;
  updateDimensionSummaryDisplay(sqMeters, sideM, sideM);
};

// -------------------------
// Crop Image Analysis
// -------------------------

function handleImagePreview(event) {
  const file = event.target.files && event.target.files[0];
  const wrap = document.getElementById("imagePreviewWrap");
  const img = document.getElementById("imagePreview");
  const meta = document.getElementById("imagePreviewMeta");

  if (!file) {
    if (wrap) wrap.classList.remove("show");
    return;
  }

  const validTypes = ["image/jpeg", "image/jpg", "image/png"];
  if (!validTypes.includes(file.type.toLowerCase())) {
    showToast("Please select a JPG, JPEG, or PNG image file.");
    event.target.value = "";
    if (wrap) wrap.classList.remove("show");
    return;
  }

  if (file.size > 10 * 1024 * 1024) {
    showToast("Image exceeds 10 MB limit. Please choose a smaller photograph.");
    event.target.value = "";
    if (wrap) wrap.classList.remove("show");
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    if (img) img.src = e.target.result;
    if (meta) meta.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    if (wrap) wrap.classList.add("show");
  };
  reader.readAsDataURL(file);
}

window.analyzeImage = async function () {
  const imageInput = document.getElementById("cropImage");
  const btn = document.getElementById("btnAnalyzeCrop");
  const resDiv = document.getElementById("imgResult");

  if (!imageInput || !imageInput.files.length) {
    showToast("Please select a crop leaf photograph first.");
    return;
  }

  const selectedCrop = getSelectedCrop();
  const formData = new FormData();
  formData.append("image", imageInput.files[0]);
  formData.append("crop", selectedCrop);

  if (btn) {
    btn.disabled = true;
    btn.textContent = "Analyzing Leaf...";
  }
  if (resDiv) {
    resDiv.innerHTML = `<div class="alert blue">Validating and running MobileNetV3 inference on leaf image...</div>`;
  }

  try {
    const resp = await fetch(`${API_BASE}/api/crop/analyze`, {
      method: "POST",
      body: formData,
    });
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || "Image analysis failed");
    }

    state.cropResult = data;
    renderCropResult(data);
    updateDashboardView();
    showToast("Leaf image analysis complete.");
  } catch (err) {
    if (resDiv) {
      resDiv.innerHTML = `<div class="alert red"><b>Error:</b> ${escapeHtml(err.message)}</div>`;
    }
    showToast(err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = window.t("btn_analyze_crop");
    }
  }
};

async function loadSampleGallery() {
  const galleryEl = document.getElementById("sampleLeafGallery");
  if (!galleryEl) return;
  try {
    const resp = await fetch(`${API_BASE}/api/crop/samples`);
    if (!resp.ok) throw new Error("Failed to fetch sample gallery");
    const data = await resp.json();
    state.sampleGallery = data.samples || [];
    if (!state.sampleGallery.length) {
      galleryEl.innerHTML = `<div class="sub">No sample leaves found in dataset folder.</div>`;
      return;
    }

    galleryEl.innerHTML = state.sampleGallery
      .map(
        (s) => `
      <div class="sample-card" onclick="analyzeSampleCard('${escapeHtml(s.class_folder)}')">
        <img src="${s.thumbnail_uri}" alt="${escapeHtml(s.crop_name)} ${escapeHtml(s.disease_name)}">
        <div class="sample-title">${escapeHtml(s.crop_name)}</div>
        <div class="sample-sub">${escapeHtml(s.disease_name)}</div>
      </div>`
      )
      .join("");
  } catch (err) {
    galleryEl.innerHTML = `<div class="sub">Sample gallery unavailable until backend is running.</div>`;
  }
}

window.analyzeSampleCard = async function (classFolder) {
  const resDiv = document.getElementById("imgResult");
  if (resDiv) {
    resDiv.innerHTML = `<div class="alert blue">Running real MobileNetV3 + Grad-CAM inference on sample leaf (${escapeHtml(classFolder)})...</div>`;
  }

  try {
    const resp = await fetch(`${API_BASE}/api/crop/analyze-sample`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ class_folder: classFolder, crop: getSelectedCrop() }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Sample analysis failed");

    if (data.crop) {
      const cropSelect = document.getElementById("cropSelect");
      if (cropSelect) cropSelect.value = data.crop;
    }
    state.cropResult = data;
    renderCropResult(data);
    updateDashboardView();
    showToast(`Diagnosed sample: ${data.crop} — ${data.disease} (${(data.confidence * 100).toFixed(1)}%)`);
  } catch (err) {
    if (resDiv) {
      resDiv.innerHTML = `<div class="alert red"><b>Error:</b> ${escapeHtml(err.message)}</div>`;
    }
    showToast(err.message);
  }
};

function renderCropResult(res) {
  const resDiv = document.getElementById("imgResult");
  if (!resDiv) return;

  if (res.status === "model_not_trained" || res.status === "unsupported_crop") {
    resDiv.innerHTML = `
      <div class="alert">
        <b>${res.status === "unsupported_crop" ? "Unsupported Crop for Image Model" : "Model Not Trained"}</b><br>
        ${escapeHtml(res.message)}
      </div>
    `;
    return;
  }

  let alertClass = "alert";
  let badgeLabel = "Uncertain — Retake Photo";
  if (res.status === "healthy") {
    alertClass = "alert green";
    badgeLabel = `Healthy Leaf (${escapeHtml(res.crop)})`;
  } else if (res.status === "diseased") {
    alertClass = "alert red";
    badgeLabel = `Possible ${escapeHtml(res.disease)} (${escapeHtml(res.crop)})`;
  }

  const confPct = res.confidence != null ? (res.confidence * 100).toFixed(1) : "0.0";
  const topRows = (res.top_predictions || [])
    .map((p) => {
      const pct = (p.confidence * 100).toFixed(1);
      return `
        <tr>
          <td>${escapeHtml(p.crop_name)} — <b>${escapeHtml(p.disease_name)}</b></td>
          <td style="width:45%">
            <div class="bar"><div class="fill" style="width:${pct}%"></div></div>
          </td>
          <td><b>${pct}%</b></td>
        </tr>
      `;
    })
    .join("");

  const qualityWarnings =
    res.quality && res.quality.warnings && res.quality.warnings.length
      ? `<div class="alert"><b>Photo Quality Check:</b> ${escapeHtml(res.quality.warnings.join(" "))}</div>`
      : "";

  const gradcamHtml =
    res.original_data_uri && res.gradcam_data_uri
      ? `
      <div class="gradcam-grid">
        <div class="gradcam-box">
          <span class="sub">Original Leaf Photo (224×224)</span>
          <img src="${res.original_data_uri}" alt="Original Leaf">
        </div>
        <div class="gradcam-box">
          <span class="sub">AI Symptom Focus — Grad-CAM Heatmap</span>
          <img src="${res.gradcam_data_uri}" alt="Grad-CAM lesion heatmap">
          <div class="sub" style="margin-top:6px">
            Hotspot area: <b>${res.hotspot_coverage_pct ?? 0}%</b> of leaf · Red/Yellow = highest model attention
          </div>
        </div>
      </div>`
      : "";

  resDiv.innerHTML = `
    <div class="${alertClass}">
      <b>${badgeLabel}</b> · Confidence: <b>${confPct}%</b>
      <div style="margin-top:6px">${escapeHtml(res.explanation)}</div>
    </div>
    ${gradcamHtml}
    ${qualityWarnings}
    ${
      topRows
        ? `<h3>Top Model Predictions</h3>
           <table>
             <thead><tr><th>Candidate Class</th><th>Probability</th><th>Score</th></tr></thead>
             <tbody>${topRows}</tbody>
           </table>`
        : ""
    }
    <p class="sub" style="margin-top:10px">${escapeHtml(res.disclaimer || "")}</p>
  `;
}

// -------------------------
// Soil Health Card Analysis
// -------------------------

window.analyzeSoil = async function () {
  const payload = { crop: getSelectedCrop() };
  let anyEntered = false;

  SOIL_PARAMS.forEach((p) => {
    const el = document.getElementById(`soil_${p.id}`);
    if (el && el.value.trim() !== "") {
      const val = parseFloat(el.value);
      if (!Number.isNaN(val)) {
        payload[p.id] = val;
        anyEntered = true;
      }
    }
  });

  const resDiv = document.getElementById("soilResult");
  try {
    const resp = await fetch(`${API_BASE}/api/soil/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!resp.ok) {
      const msg = Array.isArray(data.detail)
        ? data.detail.map((d) => `${d.loc.slice(-1)[0]}: ${d.msg}`).join("; ")
        : data.detail || "Soil analysis failed";
      throw new Error(msg);
    }

    state.soilResult = data;
    renderSoilResult(data);
    updateDashboardView();
    showToast(
      anyEntered
        ? `Soil analysis complete: Score ${data.soil_score}/100 (${data.rating})`
        : "No soil values entered — marked as unavailable."
    );
  } catch (err) {
    if (resDiv) {
      resDiv.innerHTML = `<div class="alert red"><b>Validation Error:</b> ${escapeHtml(err.message)}</div>`;
    }
    showToast(err.message);
  }
};

window.scanSoilTextReport = async function () {
  const txtEl = document.getElementById("soilPasteText");
  const statusEl = document.getElementById("soilScanStatus");
  const text = txtEl ? txtEl.value.trim() : "";
  if (!text) {
    showToast("Paste your Soil Health Card text or click 'Try Sample Lab SMS' first.");
    return;
  }

  try {
    const resp = await fetch(`${API_BASE}/api/soil/parse-text`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Could not parse text");

    const extracted = data.values || {};
    const count = data.extracted_count || Object.keys(extracted).length;
    Object.entries(extracted).forEach(([k, val]) => {
      const el = document.getElementById(`soil_${k}`);
      if (el) el.value = val;
    });
    const msg = count
      ? `Auto-filled ${count} Soil Health Card parameters (${Object.keys(extracted).join(", ")})!`
      : "No matching parameters found in text. Use format like 'N: 210, P: 16, K: 180, pH: 7.4'.";
    if (statusEl) statusEl.textContent = msg;
    showToast(msg);
    if (count > 0) {
      await analyzeSoil();
    }
  } catch (err) {
    showToast(`Scanner error: ${err.message}`);
  }
};

window.loadSampleSoilText = function () {
  const txtEl = document.getElementById("soilPasteText");
  if (txtEl) {
    txtEl.value =
      "Govt Soil Health Card Report — Village: Warangal | pH: 7.8 | EC: 0.58 dS/m | Organic Carbon (OC): 0.39% | Available N: 192 kg/ha | Phosphorus (P): 15.5 kg/ha | Potassium (K): 168 kg/ha | Sulphur (S): 8.4 ppm | Zinc (Zn): 0.46 ppm | Iron (Fe): 4.2 ppm | Boron (B): 0.41 ppm";
  }
  scanSoilTextReport();
};

function renderSoilResult(res) {
  const resDiv = document.getElementById("soilResult");
  const cardEl = document.getElementById("soilResultCard");
  if (cardEl) cardEl.style.display = "block";
  if (!resDiv) return;

  if (!res.available) {
    resDiv.innerHTML = `<div class="alert">${escapeHtml(res.message)}</div>`;
    return;
  }

  const alertClass = res.soil_score >= 75 ? "alert green" : res.soil_score >= 50 ? "alert" : "alert red";
  const problemsText = res.problems.length
    ? `Key issues: ${res.problems.join(", ")}`
    : "All entered parameters are within acceptable ranges.";

  const rows = (res.parameters || [])
    .map((p) => {
      const pillClass = p.severity === "problem" ? "problem" : p.severity === "attention" ? "attention" : "ok";
      return `
        <tr>
          <td><b>${escapeHtml(p.label)}</b></td>
          <td>${escapeHtml(p.value)} ${escapeHtml(p.unit)}</td>
          <td><span class="pill ${pillClass}">${escapeHtml(p.status_label)}</span></td>
          <td class="sub">${escapeHtml(p.reference)}</td>
          <td>${escapeHtml(p.why_it_matters)}</td>
          <td><b>${escapeHtml(p.next_step)}</b></td>
        </tr>
      `;
    })
    .join("");

  const cropNotesHtml = (res.crop_notes || []).map((n) => `<li>${escapeHtml(n)}</li>`).join("");

  resDiv.innerHTML = `
    <div class="${alertClass}">
      <b>Soil Health Score: ${res.soil_score}/100 (${escapeHtml(res.rating)})</b> — ${escapeHtml(problemsText)}
      ${res.completeness_note ? `<div class="sub" style="margin-top:4px">${escapeHtml(res.completeness_note)}</div>` : ""}
    </div>
    ${cropNotesHtml ? `<ul class="sub" style="margin:8px 0 12px">${cropNotesHtml}</ul>` : ""}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Parameter</th>
            <th>Entered Value</th>
            <th>Status</th>
            <th>Reference Range</th>
            <th>Why It Matters</th>
            <th>Recommended Next Step</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    <p class="sub" style="margin-top:10px">${escapeHtml(res.disclaimer || "")}</p>
  `;
}

// -------------------------
// Weather Intelligence
// -------------------------

window.loadWeather = async function (latArg = null, lonArg = null, notify = true) {
  let lat = latArg;
  let lon = lonArg;

  if (lat === null || lon === null) {
    if (state.activeFarm) {
      lat = state.activeFarm.latitude;
      lon = state.activeFarm.longitude;
    } else {
      const fLat = document.getElementById("farmLat").value;
      const fLon = document.getElementById("farmLon").value;
      if (fLat !== "" && fLon !== "") {
        lat = parseFloat(fLat);
        lon = parseFloat(fLon);
      }
    }
  }

  if (lat === null || lon === null || Number.isNaN(lat) || Number.isNaN(lon)) {
    if (notify) {
      showToast("Please select or save your farm location in 'Farm Profile & Location' first.");
      switchPage("farm");
    }
    return;
  }

  try {
    const resp = await fetch(`${API_BASE}/api/weather?latitude=${lat}&longitude=${lon}`);
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || "Weather request failed");
    }
    state.weatherResult = data;
    renderWeatherPage(data);
    updateDashboardView();
    if (notify) showToast("Farm weather forecast updated.");
  } catch (err) {
    if (notify) showToast(`Weather error: ${err.message}`);
  }
};

function renderWeatherPage(w) {
  if (!w || !w.current) return;
  const cur = w.current;
  const today = (w.daily && w.daily[0]) || {};

  document.getElementById("weatherTemp").textContent = `${cur.temperature ?? "--"}°C`;
  document.getElementById("weatherDesc").textContent = cur.description || "";
  document.getElementById("weatherHumidity").textContent = `${cur.humidity ?? "--"}%`;
  document.getElementById("weatherRain").textContent = `${today.precipitation_probability_max ?? "--"}%`;
  document.getElementById("weatherRainMm").textContent = `Today: ${today.precipitation_sum ?? 0} mm`;
  document.getElementById("weatherWind").textContent = `${cur.wind_speed ?? "--"} km/h`;
  document.getElementById("weatherSoilMoisture").textContent =
    cur.soil_moisture_0_1cm != null ? `Surface moisture: ${cur.soil_moisture_0_1cm} m³/m³` : "";

  // Spray windows
  const sprayEl = document.getElementById("sprayWindowsBox");
  if (sprayEl) {
    const wins = w.spray_windows || [];
    if (!wins.length) {
      sprayEl.innerHTML = `<div class="alert">No ideal low-wind, rain-free daytime spray window found in the next 48 hours. Avoid spraying in strong wind or before rain.</div>`;
    } else {
      sprayEl.innerHTML = wins
        .slice(0, 4)
        .map(
          (win) => `
        <div class="rec">
          <div class="dot">✓</div>
          <div>
            <b>${escapeHtml(win.start.replace("T", " "))} → ${escapeHtml(win.end.replace("T", " "))}</b> (${win.hours} hrs)
            <div class="sub">Max wind: ${win.max_wind_kmh} km/h · Max temp: ${win.max_temp_c}°C · Low rain risk</div>
          </div>
        </div>`
        )
        .join("");
    }
  }

  // Irrigation balance
  const irrEl = document.getElementById("irrigationBox");
  if (irrEl && w.irrigation) {
    const irr = w.irrigation;
    const cls = irr.status === "rain_sufficient" ? "alert green" : irr.status === "partial" ? "alert" : "alert blue";
    irrEl.innerHTML = `
      <div class="${cls}">
        <b>${escapeHtml(irr.advice)}</b>
        <div style="margin-top:6px">
          3-Day Forecast Rain: <b>${irr.rain_next_3_days_mm} mm</b> ·
          3-Day Reference Water Loss (ET₀): <b>${irr.et0_next_3_days_mm} mm</b> ·
          Net Water Deficit: <b>${irr.water_deficit_mm} mm</b>
        </div>
      </div>
      <p class="sub">${escapeHtml(irr.note)}</p>
    `;
  }

  // 7-day forecast table
  const tbody = document.getElementById("forecastTableBody");
  if (tbody && w.daily) {
    tbody.innerHTML = w.daily
      .map((d) => {
        const humidPill =
          d.humid_hours >= 10
            ? `<span class="pill problem">${d.humid_hours}h (High fungal risk)</span>`
            : d.humid_hours >= 5
            ? `<span class="pill attention">${d.humid_hours}h (Moderate)</span>`
            : `<span class="pill ok">${d.humid_hours}h (Low)</span>`;
        return `
          <tr>
            <td><b>${escapeHtml(d.date)}</b></td>
            <td>${escapeHtml(d.description)}</td>
            <td>${d.temp_min}°C – <b>${d.temp_max}°C</b></td>
            <td>${d.precipitation_sum} mm (${d.precipitation_probability_max ?? 0}%)</td>
            <td>${d.et0_mm ?? "--"} mm</td>
            <td>${humidPill}</td>
          </tr>
        `;
      })
      .join("");
  }

  const metaEl = document.getElementById("weatherMetaNote");
  if (metaEl) {
    metaEl.textContent = `${w.source} · Updated ${w.fetched_at || ""} · ${w.note}`;
  }
}

// -------------------------
// Integrated Risk & Advisory Engine
// -------------------------

window.runFullAdvisory = async function (saveToHistory = true) {
  const sowEl = document.getElementById("farmSowingDate");
  const areaEl = document.getElementById("farmArea");
  const sowingDate =
    (sowEl && sowEl.value) || (state.activeFarm && state.activeFarm.sowing_date) || null;
  const areaAcres =
    areaEl && areaEl.value
      ? parseFloat(areaEl.value)
      : state.activeFarm && state.activeFarm.area_acres
      ? state.activeFarm.area_acres
      : 1.0;

  const payload = {
    farm_id: state.activeFarm ? state.activeFarm.id : null,
    crop_name: getSelectedCrop(),
    growth_stage: getSelectedStage(),
    sowing_date: sowingDate,
    area_acres: areaAcres,
    crop_result: state.cropResult,
    soil_result: state.soilResult,
    weather_result: state.weatherResult,
    latitude: state.activeFarm ? state.activeFarm.latitude : null,
    longitude: state.activeFarm ? state.activeFarm.longitude : null,
    save_to_history: saveToHistory,
  };

  try {
    const resp = await fetch(`${API_BASE}/api/advisory/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.detail || "Could not generate advisory");
    }

    state.riskResult = data.risk;
    state.advisoryResult = data.advisory;
    state.calendarResult = data.calendar || null;
    if (data.soil && data.soil.available) {
      state.soilResult = data.soil;
    }

    renderAdvisoryPage(data.risk, data.advisory, data.calendar);
    await loadHistory();
    updateDashboardView();
    switchPage("advisory");
    showToast(
      saveToHistory && data.saved_assessment
        ? `Advisory generated and saved to History (#${data.saved_assessment.id}).`
        : "Advisory updated."
    );
  } catch (err) {
    showToast(`Advisory error: ${err.message}`);
  }
};

function renderAdvisoryPage(risk, adv, cal = null) {
  const badge = document.getElementById("advisoryRiskBadge");
  if (badge && risk) {
    badge.textContent = `Risk: ${risk.risk_level}${risk.risk_score != null ? ` (${risk.risk_score}/100)` : ""}`;
    badge.className =
      risk.risk_level === "HIGH"
        ? "badge danger"
        : risk.risk_level === "MODERATE"
        ? "badge warn"
        : "badge";
  }

  const summaryBox = document.getElementById("advisoryFusionSummary");
  if (summaryBox && risk && adv) {
    const comps = risk.components || {};
    const cCrop = comps.crop_disease || {};
    const cWeather = comps.weather || {};
    const cSoil = comps.soil || {};

    summaryBox.innerHTML = `
      <div class="alert ${risk.risk_level === "HIGH" ? "red" : risk.risk_level === "MODERATE" ? "" : "green"}">
        <b>${escapeHtml(adv.possible_problem)}</b>
        <div class="sub" style="margin-top:4px">${escapeHtml(risk.completeness_note || "")}</div>
      </div>
      <table>
        <thead>
          <tr><th>Evidence Source</th><th>Status</th><th>Risk Points</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>Leaf Image Screening</td>
            <td>${cCrop.available ? `<span class="pill ${cCrop.level === "high" ? "problem" : cCrop.level === "low" ? "ok" : "attention"}">${escapeHtml(cCrop.level)}</span>` : '<span class="sub">Not provided</span>'}</td>
            <td>${cCrop.available ? `<b>${cCrop.points}</b> / ${cCrop.max_points}` : "—"}</td>
          </tr>
          <tr>
            <td>Farm Weather & Microclimate</td>
            <td>${cWeather.available ? `<span class="pill ${cWeather.level === "high" ? "problem" : cWeather.level === "low" ? "ok" : "attention"}">${escapeHtml(cWeather.level)}</span>` : '<span class="sub">Not provided</span>'}</td>
            <td>${cWeather.available ? `<b>${cWeather.points}</b> / ${cWeather.max_points}` : "—"}</td>
          </tr>
          <tr>
            <td>Soil Health Card</td>
            <td>${cSoil.available ? `<span class="pill ${cSoil.level === "high" ? "problem" : cSoil.level === "low" ? "ok" : "attention"}">${escapeHtml(cSoil.level)}</span>` : '<span class="sub">Not provided</span>'}</td>
            <td>${cSoil.available ? `<b>${cSoil.points}</b> / ${cSoil.max_points}` : "—"}</td>
          </tr>
          <tr>
            <td><b>Integrated Risk Score</b></td>
            <td><b>${escapeHtml(risk.risk_level)}</b></td>
            <td><b>${risk.risk_score ?? "--"} / 100</b></td>
          </tr>
        </tbody>
      </table>
      <h3>Why This Warning?</h3>
      <ul style="margin:6px 0 0;padding-left:18px;font-size:13px">
        ${(adv.why_this_warning || []).map((r) => `<li style="margin-bottom:4px">${escapeHtml(r)}</li>`).join("")}
      </ul>
    `;
  }

  const actionsBox = document.getElementById("advisoryActionsList");
  if (actionsBox && adv) {
    actionsBox.innerHTML = (adv.recommended_actions || [])
      .map(
        (a) => `
      <div class="rec">
        <div class="dot ${a.priority === "high" ? "high" : ""}">${a.step}</div>
        <div>
          <b>${escapeHtml(a.title)}</b>
          <div class="sub">${escapeHtml(a.detail)}</div>
        </div>
      </div>`
      )
      .join("");
  }

  const extraBox = document.getElementById("advisoryExtraDetails");
  if (extraBox && adv) {
    const soilRows = (adv.soil_attention || [])
      .map(
        (s) => `
      <tr>
        <td><b>${escapeHtml(s.parameter)}</b></td>
        <td>${escapeHtml(s.value)} (${escapeHtml(s.status)})</td>
        <td>${escapeHtml(s.next_step)}</td>
      </tr>`
      )
      .join("");

    const ws = adv.weather_summary;
    extraBox.innerHTML = `
      <div class="grid" style="margin-top:16px">
        <div class="card w6">
          <h2>Soil Attention Summary</h2>
          <table>
            <thead><tr><th>Parameter</th><th>Status</th><th>Action</th></tr></thead>
            <tbody>${soilRows}</tbody>
          </table>
        </div>
        <div class="card w6">
          <h2>Weather & Field Timing Summary</h2>
          ${
            ws
              ? `<p><b>Current:</b> ${escapeHtml(ws.current_conditions)}</p>
                 <p><b>Irrigation Hint:</b> ${escapeHtml(ws.irrigation_advice || "—")}</p>
                 <p><b>Next Spray / Work Window:</b> ${escapeHtml(ws.next_spray_window)}</p>`
              : `<div class="empty-state">Select a farm location to include live weather timing in your advisory.</div>`
          }
          <div class="alert blue" style="margin-top:12px">
            <b>${escapeHtml(adv.helpline.name)}: ${escapeHtml(adv.helpline.phone)}</b><br>
            <span class="sub">${escapeHtml(adv.helpline.note)}</span>
          </div>
        </div>
      </div>
      <p class="sub" style="margin-top:12px">${escapeHtml(adv.disclaimer)}</p>
    `;
  }

  renderCropCalendar(cal || state.calendarResult);
}

function renderCropCalendar(cal) {
  const calBox = document.getElementById("advisoryCalendarSection");
  if (!calBox) return;
  if (!cal || !cal.timeline) {
    calBox.innerHTML = "";
    return;
  }

  const stageNodes = (cal.timeline || [])
    .map(
      (s) => `
    <div class="stage-node ${s.status === "current" ? "active" : s.status}">
      <div class="stage-day">${escapeHtml(s.day_range)}${s.start_date ? ` (${escapeHtml(s.start_date.slice(5))})` : ""}</div>
      <div class="stage-name">${escapeHtml(s.title)}</div>
      <div class="stage-focus">${escapeHtml(s.tasks)}</div>
    </div>`
    )
    .join("");

  const pa = cal.plot_area || { acres: 1, guntas: 40 };
  const wb = cal.water_balance_plot;
  const wbHtml = wb
    ? `
    <div class="alert blue" style="margin-top:12px">
      <b>💧 3-Day Plot Water Calculator (${pa.acres} ac / ${pa.guntas} guntas):</b>
      Net water deficit is <b>${wb.deficit_mm} mm</b> (Rain: ${wb.rain_mm} mm vs ET₀: ${wb.et0_mm} mm).
      Estimated irrigation volume needed across your plot: <b>${(wb.net_deficit_liters || 0).toLocaleString()} Liters</b>.
    </div>`
    : "";

  const fym = cal.organic_manure_plan || cal.organic_manure_guide || {};
  const activeStageObj = (cal.timeline || []).find((s) => s.status === "current") || cal.timeline[0] || {};
  const dasInfo =
    cal.days_after_sowing != null
      ? `Day <b>${cal.days_after_sowing}</b> of ~${cal.duration_days} days`
      : `Total cycle: ~${cal.duration_days} days (enter Sowing Date in Farm Profile for exact day count)`;

  calBox.innerHTML = `
    <div class="card" style="margin-bottom:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
        <div>
          <h2>📅 Personalized Crop Stage Calendar & Plot Input Calculator (${escapeHtml(cal.crop)})</h2>
          <p class="sub">
            ${dasInfo}
            ${cal.expected_harvest_date ? ` · Expected Harvest: <b>${escapeHtml(cal.expected_harvest_date)}</b>` : ""}
          </p>
        </div>
        <span class="badge">Active Stage: ${escapeHtml(activeStageObj.title || cal.detected_stage)}</span>
      </div>

      <div class="stage-timeline">
        ${stageNodes}
      </div>

      <div class="grid" style="margin-top:14px">
        <div class="w6">
          <div class="alert green" style="margin:0">
            <b>Current Stage Focus (${escapeHtml(activeStageObj.title || cal.detected_stage)}):</b><br>
            ${escapeHtml(activeStageObj.tasks || "")}
          </div>
        </div>
        <div class="w6">
          <div class="alert" style="margin:0">
            <b>🌱 Basal Organic Manure Plan (${pa.acres} Acres / ${pa.guntas} Guntas):</b><br>
            ${escapeHtml(fym.note || "")} (~<b>${fym.tractor_trolleys_approx ?? "--"} tractor trolleys</b>).
          </div>
        </div>
      </div>
      ${wbHtml}
    </div>
  `;
}

// Text-to-Speech (TTS) audio readout for farmers
window.speakAdvisory = function () {
  if (!("speechSynthesis" in window)) {
    showToast("Audio speech is not supported in this browser.");
    return;
  }
  if (!state.advisoryResult || !state.advisoryResult.plain_text_summary) {
    showToast("Generate an advisory first to listen to it.");
    return;
  }
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(state.advisoryResult.plain_text_summary);
  const langMap = { te: "te-IN", hi: "hi-IN", en: "en-IN" };
  const targetLang = langMap[window.currentLang] || "en-IN";
  utter.lang = targetLang;
  const voices = window.speechSynthesis.getVoices ? window.speechSynthesis.getVoices() : [];
  const matchingVoice = voices.find((v) => v.lang && v.lang.toLowerCase().startsWith(targetLang.slice(0, 2)));
  if (matchingVoice) utter.voice = matchingVoice;
  utter.rate = 0.95;
  window.speechSynthesis.speak(utter);
  showToast("Reading advisory aloud...");
};

window.stopSpeakingAdvisory = function () {
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
};

window.copyAdvisoryForWhatsApp = async function () {
  if (!state.advisoryResult || !state.advisoryResult.plain_text_summary) {
    showToast("Generate an advisory first before copying.");
    return;
  }
  try {
    await navigator.clipboard.writeText(state.advisoryResult.plain_text_summary);
    showToast("Advisory summary copied! You can paste it into WhatsApp or SMS.");
  } catch (e) {
    showToast("Could not copy automatically.");
  }
};

// -------------------------
// Dashboard & History
// -------------------------

function updateJourneyStrip() {
  const jFarm = document.getElementById("jStepFarm");
  const jCrop = document.getElementById("jStepCrop");
  const jSoil = document.getElementById("jStepSoil");
  const jAdv = document.getElementById("jStepAdv");

  const farmDone = Boolean(state.activeFarm && state.activeFarm.latitude != null);
  const cropDone = Boolean(state.cropResult && state.cropResult.available);
  const soilDone = Boolean(state.soilResult && state.soilResult.available);
  const advDone = Boolean(state.advisoryResult && state.riskResult);

  if (jFarm) jFarm.classList.toggle("done", farmDone);
  if (jCrop) jCrop.classList.toggle("done", cropDone);
  if (jSoil) jSoil.classList.toggle("done", soilDone);
  if (jAdv) jAdv.classList.toggle("done", advDone);
}

function updateDashboardView() {
  updateJourneyStrip();
  const cropEl = document.getElementById("dashCropMetric");
  const cropSubEl = document.getElementById("dashCropSub");
  const diseaseEl = document.getElementById("dashDiseaseMetric");
  const diseaseSubEl = document.getElementById("dashDiseaseSub");
  const soilEl = document.getElementById("dashSoilMetric");
  const soilBarEl = document.getElementById("dashSoilBar");
  const riskEl = document.getElementById("dashRiskMetric");
  const riskBarEl = document.getElementById("dashRiskBar");

  // Use either current session results or latest saved assessment from SQLite
  const latestSaved = state.assessments && state.assessments.length ? state.assessments[0] : null;

  const cropName = getSelectedCrop();
  const stageName = getSelectedStage();
  if (cropEl) cropEl.textContent = cropName;
  if (cropSubEl) cropSubEl.textContent = `Stage: ${stageName}`;

  // Leaf diagnosis metric
  if (state.cropResult && state.cropResult.available && state.cropResult.disease) {
    const conf = state.cropResult.confidence != null ? `${(state.cropResult.confidence * 100).toFixed(0)}% conf.` : "";
    diseaseEl.textContent = state.cropResult.is_uncertain
      ? `Uncertain (${state.cropResult.disease})`
      : state.cropResult.disease;
    diseaseEl.className = state.cropResult.is_healthy ? "good" : "danger";
    diseaseSubEl.textContent = `Current session · ${conf}`;
  } else if (latestSaved && latestSaved.predicted_disease) {
    diseaseEl.textContent = latestSaved.predicted_disease;
    diseaseEl.className = latestSaved.predicted_disease === "Healthy" ? "good" : "warn";
    diseaseSubEl.textContent = `Last saved (${latestSaved.assessment_date.slice(0, 10)})`;
  } else {
    diseaseEl.textContent = "Not checked";
    diseaseEl.className = "";
    diseaseSubEl.textContent = "Upload a leaf photo in Crop Leaf Analysis";
  }

  // Soil metric
  const soilScore =
    state.soilResult && state.soilResult.available
      ? state.soilResult.soil_score
      : latestSaved && latestSaved.soil_score != null
      ? latestSaved.soil_score
      : null;

  if (soilScore != null) {
    soilEl.textContent = `${soilScore}/100`;
    soilEl.className = soilScore >= 75 ? "good" : soilScore >= 50 ? "warn" : "danger";
    if (soilBarEl) soilBarEl.style.width = `${soilScore}%`;
  } else {
    soilEl.textContent = "No card";
    soilEl.className = "";
    if (soilBarEl) soilBarEl.style.width = "0%";
  }

  // Risk metric
  const riskScore =
    state.riskResult && state.riskResult.available
      ? state.riskResult.risk_score
      : latestSaved && latestSaved.risk_score != null
      ? latestSaved.risk_score
      : null;
  const riskLevel =
    state.riskResult && state.riskResult.available
      ? state.riskResult.risk_level
      : latestSaved && latestSaved.risk_level
      ? latestSaved.risk_level
      : null;

  if (riskScore != null && riskLevel) {
    riskEl.textContent = `${riskLevel} · ${riskScore}/100`;
    riskEl.className = riskLevel === "HIGH" ? "danger" : riskLevel === "MODERATE" ? "warn" : "good";
    if (riskBarEl) riskBarEl.style.width = `${riskScore}%`;
  } else {
    riskEl.textContent = "Not run";
    riskEl.className = "";
    if (riskBarEl) riskBarEl.style.width = "0%";
  }

  // Dashboard Weather Card
  const dashWeatherBox = document.getElementById("dashWeatherBox");
  if (dashWeatherBox) {
    if (state.weatherResult && state.weatherResult.current) {
      const c = state.weatherResult.current;
      const d0 = (state.weatherResult.daily && state.weatherResult.daily[0]) || {};
      const irr = state.weatherResult.irrigation || {};
      dashWeatherBox.innerHTML = `
        <div class="weather-grid">
          <div class="weather-box"><span class="sub">Temp</span><strong>${c.temperature}°C</strong></div>
          <div class="weather-box"><span class="sub">Humidity</span><strong>${c.humidity}%</strong></div>
          <div class="weather-box"><span class="sub">Rain Prob.</span><strong>${d0.precipitation_probability_max ?? 0}%</strong></div>
          <div class="weather-box"><span class="sub">Wind</span><strong>${c.wind_speed} km/h</strong></div>
        </div>
        <div class="alert blue" style="margin-top:12px">
          <b>${escapeHtml(c.description)}:</b> ${escapeHtml(irr.advice || "")}
        </div>
      `;
    } else {
      dashWeatherBox.innerHTML = `
        <div class="empty-state">
          No farm location selected yet.<br><br>
          <button class="secondary" onclick="switchPage('farm')">Select Farm Location</button>
        </div>
      `;
    }
  }

  // Dashboard Recent Recommendations Card
  const dashAdvBox = document.getElementById("dashAdvisoryBox");
  if (dashAdvBox) {
    if (state.advisoryResult && state.advisoryResult.recommended_actions) {
      const topActs = state.advisoryResult.recommended_actions.slice(0, 3);
      dashAdvBox.innerHTML = `
        <div class="alert ${state.advisoryResult.risk_level === "HIGH" ? "red" : "green"}">
          <b>${escapeHtml(state.advisoryResult.possible_problem)}</b>
        </div>
        ${topActs
          .map(
            (a) => `
          <div class="rec">
            <div class="dot">${a.step}</div>
            <div><b>${escapeHtml(a.title)}</b><br><span class="sub">${escapeHtml(a.detail)}</span></div>
          </div>`
          )
          .join("")}
      `;
    } else {
      dashAdvBox.innerHTML = `
        <div class="empty-state">
          Upload a leaf photo, enter Soil Health Card values, or load farm weather, then click
          <b>"Generate & Save Full Advisory"</b> to see tailored recommendations here.
        </div>
      `;
    }
  }
}

window.loadHistory = async function () {
  try {
    const farmQuery = state.activeFarm ? `?farm_id=${state.activeFarm.id}` : "";
    const resp = await fetch(`${API_BASE}/api/assessments${farmQuery}`);
    if (!resp.ok) return;
    const data = await resp.json();
    state.assessments = data.assessments || [];
    renderHistoryTable();
    renderTrendChart();
  } catch (err) {
    console.error("Failed to load history:", err);
  }
};

function renderHistoryTable() {
  const tbody = document.getElementById("historyTableBody");
  if (!tbody) return;

  if (!state.assessments.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align:center;padding:20px" class="sub">
          No assessments saved in SQLite yet. Run an analysis and click "Generate & Save Full Advisory".
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = state.assessments
    .map((a) => {
      const pillCls = a.risk_level === "HIGH" ? "problem" : a.risk_level === "MODERATE" ? "attention" : "ok";
      const confStr = a.model_confidence != null ? ` (${(a.model_confidence * 100).toFixed(0)}%)` : "";
      return `
        <tr>
          <td>#${a.id} · ${escapeHtml((a.assessment_date || "").slice(0, 16))}</td>
          <td><b>${escapeHtml(a.crop_name)}</b> <span class="sub">(${escapeHtml(a.growth_stage || "—")})</span></td>
          <td>${escapeHtml(a.predicted_disease || "Not run")}${escapeHtml(confStr)}</td>
          <td>${a.soil_score != null ? `<b>${a.soil_score}</b>/100` : "—"}</td>
          <td><span class="pill ${pillCls}">${escapeHtml(a.risk_level || "—")} (${a.risk_score ?? "--"})</span></td>
          <td>
            <button class="secondary" onclick="viewAssessmentDetail(${a.id})">View Advisory</button>
            <button class="danger-btn" onclick="deleteAssessmentById(${a.id})">Delete</button>
          </td>
        </tr>
      `;
    })
    .join("");
}

function renderTrendChart() {
  const canvas = document.getElementById("riskChart");
  const emptyNote = document.getElementById("chartEmptyNote");
  if (!canvas || typeof Chart === "undefined") return;

  const items = [...state.assessments].reverse().slice(-10);
  if (!items.length) {
    if (state.historyChart) {
      state.historyChart.destroy();
      state.historyChart = null;
    }
    canvas.style.display = "none";
    if (emptyNote) emptyNote.style.display = "block";
    return;
  }

  canvas.style.display = "block";
  if (emptyNote) emptyNote.style.display = "none";

  const labels = items.map((a) => `#${a.id} (${(a.assessment_date || "").slice(5, 10)})`);
  const riskData = items.map((a) => a.risk_score ?? null);
  const soilData = items.map((a) => a.soil_score ?? null);

  if (state.historyChart) {
    state.historyChart.destroy();
  }

  state.historyChart = new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Integrated Risk Score (0-100)",
          data: riskData,
          borderColor: "#a13a31",
          backgroundColor: "rgba(161, 58, 49, 0.1)",
          tension: 0.3,
        },
        {
          label: "Soil Health Score (0-100)",
          data: soilData,
          borderColor: "#3b6e52",
          backgroundColor: "rgba(59, 110, 82, 0.1)",
          tension: 0.3,
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: { min: 0, max: 100, grid: { color: "#eef1ec" } },
        x: { grid: { display: false } },
      },
    },
  });
}

window.viewAssessmentDetail = async function (id) {
  try {
    const resp = await fetch(`${API_BASE}/api/assessments/${id}`);
    if (!resp.ok) throw new Error("Could not load assessment");
    const rec = await resp.json();
    if (rec.details && rec.advisory) {
      state.riskResult = rec.details;
      state.advisoryResult = rec.advisory;
      renderAdvisoryPage(rec.details, rec.advisory);
      switchPage("advisory");
      showToast(`Loaded saved assessment #${id} from ${rec.assessment_date.slice(0, 10)}`);
    }
  } catch (err) {
    showToast(err.message);
  }
};

window.deleteAssessmentById = async function (id) {
  try {
    const resp = await fetch(`${API_BASE}/api/assessments/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error("Failed to delete assessment");
    await loadHistory();
    updateDashboardView();
    showToast(`Assessment #${id} deleted.`);
  } catch (err) {
    showToast("Could not delete assessment.");
  }
};

// -------------------------
// Start a New Farm (Beginner Wizard)
// -------------------------

function getEnteredSoilValuesMap() {
  const vals = {};
  SOIL_PARAMS.forEach((p) => {
    const el = document.getElementById(`soil_${p.id}`);
    if (el && el.value.trim() !== "") {
      const v = parseFloat(el.value);
      if (!Number.isNaN(v)) vals[p.id] = v;
    }
  });
  return vals;
}

window.runNewFarmWizard = async function (notify = true) {
  const seasonVal = (document.getElementById("nfSeason") || {}).value || "auto";
  const waterVal = (document.getElementById("nfWater") || {}).value || "limited";
  const budgetVal = (document.getElementById("nfBudget") || {}).value || "low";
  const labourVal = (document.getElementById("nfLabour") || {}).value || "family";
  const areaVal = parseFloat((document.getElementById("nfArea") || {}).value) || 1.0;
  const focusCropVal = (document.getElementById("nfFocusCrop") || {}).value || null;
  const soilMap = getEnteredSoilValuesMap();

  const payload = {
    season: seasonVal === "auto" ? null : seasonVal,
    water_source: waterVal,
    budget: budgetVal,
    labour: labourVal,
    area_acres: areaVal,
    soil_ph: soilMap.pH ?? null,
    soil_ec: soilMap.EC ?? null,
    soil_n: soilMap.N ?? null,
    selected_crop: focusCropVal,
  };

  const wrap = document.getElementById("newFarmResultsWrap");
  try {
    const resp = await fetch(`${API_BASE}/api/new-farm/plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Failed to generate new farm plan");

    renderNewFarmPlan(data);
    if (notify) {
      showToast(`Top recommended crop for ${data.season.name}: ${data.recommended_crops[0].crop_name}`);
    }
  } catch (err) {
    if (wrap) wrap.innerHTML = `<div class="alert red">${escapeHtml(err.message)}</div>`;
    if (notify) showToast(err.message);
  }
};

window.selectNewFarmCrop = function (cropKey, cropName) {
  const focusEl = document.getElementById("nfFocusCrop");
  if (focusEl) focusEl.value = cropKey;
  const inpCrop = document.getElementById("inpCrop");
  if (inpCrop) inpCrop.value = cropName;
  const cropSel = document.getElementById("cropSelect");
  if (cropSel) cropSel.value = cropName;
  window.runNewFarmWizard(true);
};

function renderNewFarmPlan(data) {
  const wrap = document.getElementById("newFarmResultsWrap");
  if (!wrap || !data) return;

  const cropRows = (data.recommended_crops || [])
    .map((c, idx) => {
      const pillCls =
        c.suitability_score >= 75 ? "ok" : c.suitability_score >= 55 ? "attention" : "problem";
      const whyList = (c.why_it_fits || []).map((r) => `✓ ${escapeHtml(r)}`).join("<br>");
      const cautionList = (c.cautions || []).map((r) => `⚠️ ${escapeHtml(r)}`).join("<br>");
      return `
        <tr>
          <td><b>#${idx + 1} ${escapeHtml(c.crop_name)}</b><div class="sub">${escapeHtml(c.category)} · ${c.duration_days} days</div></td>
          <td><span class="pill ${pillCls}">${c.suitability_score}/100 (${escapeHtml(c.suitability_label)})</span></td>
          <td>Water: <b>${escapeHtml(c.water_need)}</b><br>Cost: <b>${escapeHtml(c.cost_level)}</b> · Labour: <b>${escapeHtml(c.labour_need)}</b></td>
          <td>${escapeHtml(c.sowing_method)}<div class="sub">Spacing: ${escapeHtml(c.spacing)} · pH ${escapeHtml(c.preferred_ph)}</div></td>
          <td style="font-size:12.5px">${whyList}${cautionList ? `<div style="margin-top:4px;color:var(--warn)">${cautionList}</div>` : ""}</td>
          <td>
            <button class="secondary" onclick="selectNewFarmCrop('${escapeHtml(c.crop_key)}', '${escapeHtml(c.crop_name)}')">View Checklist</button>
          </td>
        </tr>
      `;
    })
    .join("");

  const sp = data.selected_crop_plan || {};
  const checklistHtml = (sp.pre_sowing_checklist || [])
    .map(
      (item) => `
      <div class="rec">
        <div class="dot">${item.step}</div>
        <div>
          <b>${escapeHtml(item.title)}</b>
          <div class="sub">${escapeHtml(item.detail)}</div>
        </div>
      </div>`
    )
    .join("");

  const stagesHtml = (sp.stages || [])
    .map(
      (st) => `
      <div class="stage-node active">
        <div class="stage-day">Days ${st.days[0]}–${st.days[1]}</div>
        <div class="stage-name">${escapeHtml(st.title)}</div>
        <div class="stage-focus">${escapeHtml(st.tasks)}</div>
      </div>`
    )
    .join("");

  const schemesHtml = (data.schemes_and_help || [])
    .map(
      (sc) => `
      <tr>
        <td><b>${escapeHtml(sc.name)}</b></td>
        <td>${escapeHtml(sc.what)}</td>
        <td>${escapeHtml(sc.how)} ${sc.link ? `· <a href="${escapeHtml(sc.link)}" target="_blank" rel="noopener">Official Portal ↗</a>` : ""}</td>
      </tr>`
    )
    .join("");

  wrap.innerHTML = `
    <div class="card" style="margin-bottom:18px">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
        <div>
          <h2>Step 4: Ranked Crop Shortlist for ${escapeHtml(data.season.name)}</h2>
          <p class="sub">${escapeHtml(data.season.about)} · Plot: <b>${data.resources.area_acres} ac (${data.resources.area_guntas} guntas)</b></p>
        </div>
        <button onclick="switchPage('inputs')">🛒 See What Fertilizers & Inputs to Buy →</button>
      </div>
      <div class="table-wrap" style="margin-top:10px">
        <table>
          <thead>
            <tr>
              <th>Crop & Duration</th>
              <th>Suitability</th>
              <th>Water / Cost / Labour</th>
              <th>Sowing & Spacing</th>
              <th>Why It Fits / Cautions</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>${cropRows}</tbody>
        </table>
      </div>
    </div>

    <div class="grid" style="margin-bottom:18px">
      <div class="card w6">
        <h2>Step 5: Before You Sow — Checklist for ${escapeHtml(sp.crop_name)}</h2>
        <p class="sub">Duration: ~${sp.duration_days} days · Spacing: <b>${escapeHtml(sp.spacing)}</b> · Preferred pH: ${escapeHtml(sp.preferred_ph)}</p>
        <div style="margin-top:10px">${checklistHtml}</div>
      </div>
      <div class="card w6">
        <h2>Step 6: Season-Long Stage Roadmap (${escapeHtml(sp.crop_name)})</h2>
        <p class="sub">${escapeHtml(sp.heat_note || "Follow stage-wise irrigation and scouting tasks below.")}</p>
        <div class="stage-timeline" style="grid-template-columns:1fr;margin-top:10px">${stagesHtml}</div>
      </div>
    </div>

    <div class="card">
      <h2>Step 7: Free Government Support, Soil Testing & Helplines for New Farmers</h2>
      <div class="table-wrap" style="margin-top:10px">
        <table>
          <thead>
            <tr><th>Scheme / Institution</th><th>What Support You Get</th><th>How to Access</th></tr>
          </thead>
          <tbody>${schemesHtml}</tbody>
        </table>
      </div>
      <p class="sub" style="margin-top:10px">${escapeHtml(data.disclaimer)}</p>
    </div>
  `;
}

// -------------------------
// What to Buy — Fertilizers, Bio-Inputs, IPM & Weed Guide
// -------------------------

window.fillSampleBagPrices = function () {
  document.getElementById("priceUrea").value = 266;
  document.getElementById("priceDap").value = 1350;
  document.getElementById("priceSsp").value = 550;
  document.getElementById("priceMop").value = 1700;
  window.runInputsAdvisor(true);
};

window.runInputsAdvisor = async function (notify = true) {
  const cropName = (document.getElementById("inpCrop") || {}).value || getSelectedCrop();
  const areaAcres = parseFloat((document.getElementById("inpArea") || {}).value) || 1.0;
  const soilMap = getEnteredSoilValuesMap();

  const prices = {};
  const pUrea = parseFloat((document.getElementById("priceUrea") || {}).value);
  const pDap = parseFloat((document.getElementById("priceDap") || {}).value);
  const pSsp = parseFloat((document.getElementById("priceSsp") || {}).value);
  const pMop = parseFloat((document.getElementById("priceMop") || {}).value);
  if (!Number.isNaN(pUrea) && pUrea > 0) prices.urea = pUrea;
  if (!Number.isNaN(pDap) && pDap > 0) prices.dap = pDap;
  if (!Number.isNaN(pSsp) && pSsp > 0) prices.ssp = pSsp;
  if (!Number.isNaN(pMop) && pMop > 0) prices.mop = pMop;

  const payload = {
    crop_name: cropName,
    area_acres: areaAcres,
    soil_values: Object.keys(soilMap).length ? soilMap : null,
    crop_result: state.cropResult,
    prices: Object.keys(prices).length ? prices : null,
  };

  const wrap = document.getElementById("inputsResultsWrap");
  try {
    const resp = await fetch(`${API_BASE}/api/inputs/recommend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Could not calculate inputs");

    renderInputsAdvisor(data);
    if (notify) {
      showToast(`Shopping list calculated for ${data.area_acres} ac (${data.area_guntas} guntas) of ${data.crop}.`);
    }
  } catch (err) {
    if (wrap) wrap.innerHTML = `<div class="alert red">${escapeHtml(err.message)}</div>`;
    if (notify) showToast(err.message);
  }
};

function renderInputsAdvisor(data) {
  const wrap = document.getElementById("inputsResultsWrap");
  if (!wrap || !data) return;

  const fp = data.fertilizer_plan || {};
  let fertHtml = "";
  if (!fp.available) {
    fertHtml = `<div class="alert">${escapeHtml(fp.message)}</div>`;
  } else {
    const renderOptRows = (items) =>
      (items || [])
        .map(
          (i) => `
        <tr>
          <td><b>${escapeHtml(i.product)}</b></td>
          <td><b>${i.kg} kg</b></td>
          <td>${i.bags_exact} bags (${i.bag_kg} kg bag) → <b>Buy ${i.bags_to_buy} bag(s)</b></td>
          <td>${i.estimated_cost != null ? `<b>₹${i.estimated_cost.toLocaleString()}</b>` : '<span class="sub">Enter bag price above</span>'}</td>
        </tr>`
        )
        .join("");

    const schedHtml = (fp.split_schedule || [])
      .map(
        (s) => `
      <div class="rec">
        <div class="dot">D${s.day}</div>
        <div>
          <b>${escapeHtml(s.when)}</b>: ${escapeHtml((s.items || []).join(" + "))}
          <div class="sub">${escapeHtml(s.note)}</div>
        </div>
      </div>`
      )
      .join("");

    fertHtml = `
      <div class="alert green">
        <b>Recommended Fertilizer Combination: Option ${escapeHtml(fp.recommended_option)}</b> — ${escapeHtml(fp.why_option)}
        <div class="sub" style="margin-top:4px">
          Nutrient target for ${data.area_acres} ac (${data.area_guntas} guntas):
          <b>N: ${fp.dose_for_plot_kg.N} kg</b> · <b>P₂O₅: ${fp.dose_for_plot_kg.P2O5} kg</b> · <b>K₂O: ${fp.dose_for_plot_kg.K2O} kg</b>
          (${escapeHtml(fp.source)})
        </div>
      </div>
      ${
        (fp.soil_adjustments || []).length
          ? `<ul class="sub" style="margin:6px 0 12px">${fp.soil_adjustments.map((a) => `<li>${escapeHtml(a)}</li>`).join("")}</ul>`
          : ""
      }
      <div class="grid">
        <div class="w6">
          <h3>${escapeHtml(fp.option_a.title)} ${fp.recommended_option === "A" ? '<span class="pill ok">Recommended</span>' : ""}</h3>
          <table>
            <thead><tr><th>Fertilizer</th><th>Plot Need</th><th>Bags</th><th>Est. Cost</th></tr></thead>
            <tbody>${renderOptRows(fp.option_a.items)}</tbody>
          </table>
        </div>
        <div class="w6">
          <h3>${escapeHtml(fp.option_b.title)} ${fp.recommended_option === "B" ? '<span class="pill ok">Recommended</span>' : ""}</h3>
          <table>
            <thead><tr><th>Fertilizer</th><th>Plot Need</th><th>Bags</th><th>Est. Cost</th></tr></thead>
            <tbody>${renderOptRows(fp.option_b.items)}</tbody>
          </table>
          <div class="sub" style="margin-top:4px">Also supplies ~<b>${fp.option_b.sulphur_supplied_kg} kg Sulphur (S)</b> to the soil.</div>
        </div>
      </div>
      <h3 style="margin-top:16px">Split Application Schedule (When to Apply)</h3>
      <div>${schedHtml}</div>
    `;
  }

  const shopRows = (data.shopping_list || [])
    .map(
      (s) => `
    <tr>
      <td><span class="pill ok">${escapeHtml(s.category)}</span></td>
      <td><b>${escapeHtml(s.item)}</b></td>
      <td>${escapeHtml(s.quantity)}</td>
      <td>${s.cost != null ? `<b>₹${s.cost.toLocaleString()}</b>` : "—"}</td>
    </tr>`
    )
    .join("");

  const pp = data.plant_protection || {};
  const detectedHtml = pp.detected_problem
    ? `<div class="alert red">
         <b>Active Leaf Problem Detected: ${escapeHtml(pp.detected_problem.name)} (${escapeHtml(pp.detected_problem.type)})</b>
         <div class="sub">${escapeHtml(pp.detected_problem.source)} — ${escapeHtml(pp.detected_problem.about)}</div>
       </div>`
    : "";

  const toolsRows = (pp.monitoring_tools || [])
    .map(
      (t) => `
    <tr>
      <td><b>${escapeHtml(t.product)}</b></td>
      <td>${escapeHtml((t.for || []).join(", "))}</td>
      <td>${escapeHtml(t.why)} <div class="sub">${escapeHtml(t.how)}</div></td>
    </tr>`
    )
    .join("");

  const bioRows = (pp.bio_options || [])
    .map(
      (b) => `
    <tr>
      <td><b>${escapeHtml(b.product)}</b></td>
      <td>${escapeHtml(b.why)}</td>
      <td>${escapeHtml(b.how)}</td>
    </tr>`
    )
    .join("");

  const wm = data.weed_management || {};

  wrap.innerHTML = `
    <div class="card" style="margin-bottom:18px">
      <h2>2. Complete Plot Shopping List — ${escapeHtml(data.crop)} (${data.area_acres} Acres / ${data.area_guntas} Guntas)</h2>
      ${
        data.estimated_fertilizer_cost != null
          ? `<div class="alert blue"><b>Estimated Fertilizer Cost (Recommended Option): ₹${data.estimated_fertilizer_cost.toLocaleString()}</b></div>`
          : ""
      }
      <div class="table-wrap">
        <table>
          <thead><tr><th>Category</th><th>Input / Item to Buy</th><th>Plot-Scaled Quantity</th><th>Est. Cost</th></tr></thead>
          <tbody>${shopRows}</tbody>
        </table>
      </div>
    </div>

    <div class="card" style="margin-bottom:18px">
      <h2>3. Fertilizer Calculator & Split Schedule (Urea / DAP / SSP / MOP)</h2>
      ${fertHtml}
    </div>

    <div class="grid" style="margin-bottom:18px">
      <div class="card w6">
        <h2>4. Pest & Disease Protection (IPM Buying Guide)</h2>
        ${detectedHtml}
        <h3>Low-Cost Traps & Monitoring Tools</h3>
        <table>
          <thead><tr><th>Tool</th><th>Target Pest</th><th>Why & How to Use</th></tr></thead>
          <tbody>${toolsRows || '<tr><td colspan="3">Scout crop weekly for pests.</td></tr>'}</tbody>
        </table>
        <h3 style="margin-top:14px">Biological & Botanical Products (First-Line Sprays)</h3>
        <table>
          <thead><tr><th>Bio-Input</th><th>What It Controls</th><th>Usage</th></tr></thead>
          <tbody>${bioRows}</tbody>
        </table>
      </div>

      <div class="card w6">
        <h2>5. Weed Management, Herbicides & Safe Buying Rules</h2>
        <div class="alert">
          <b>Critical Weed-Free Period:</b> First <b>${wm.critical_weed_free_days} days</b> after sowing.
        </div>
        <ul style="padding-left:18px;font-size:13.5px">
          ${(wm.practices || []).map((p) => `<li style="margin-bottom:6px">${escapeHtml(p)}</li>`).join("")}
        </ul>
        <p class="sub" style="margin-top:8px"><b>Herbicide Guidance:</b> ${escapeHtml(wm.herbicide_note || "")}</p>

        <h3 style="margin-top:14px">Where to Buy Genuine Inputs Safely</h3>
        <ul style="padding-left:18px;font-size:13px">
          ${(data.where_to_buy || []).map((w) => `<li style="margin-bottom:5px"><b>${escapeHtml(w.name)}:</b> ${escapeHtml(w.note)}</li>`).join("")}
        </ul>
      </div>
    </div>
    <p class="sub">${escapeHtml(data.disclaimer)}</p>
  `;
}
